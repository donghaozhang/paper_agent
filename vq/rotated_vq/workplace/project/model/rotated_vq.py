import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class VectorQuantizer(nn.Module):
    """
    Vector Quantization layer with rotation transformation
    """
    def __init__(self, num_embeddings, embedding_dim, commitment_cost=0.25, use_rotation=True, ema_decay=0.99):
        super(VectorQuantizer, self).__init__()
        
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.commitment_cost = commitment_cost
        self.use_rotation = use_rotation
        self.ema_decay = ema_decay
        self.use_ema = ema_decay > 0
        
        # Initialize embeddings
        self.embedding = nn.Embedding(self.num_embeddings, self.embedding_dim)
        self.embedding.weight.data.uniform_(-1.0 / self.num_embeddings, 1.0 / self.num_embeddings)
        
        # EMA related variables
        if self.use_ema:
            self.register_buffer('ema_cluster_size', torch.zeros(num_embeddings))
            self.register_buffer('ema_w', self.embedding.weight.data.clone())
    
    def compute_rotation_matrix(self, z_e, q):
        """
        Compute the rotation matrix that aligns z_e with q
        """
        # Normalize vectors
        z_e_norm = F.normalize(z_e, dim=-1)
        q_norm = F.normalize(q, dim=-1)
        
        # Compute the rotation matrix using Householder transformation
        v = z_e_norm - q_norm
        v_norm = torch.norm(v, dim=-1, keepdim=True)
        mask = (v_norm > 1e-5).float()
        v = mask * v / (v_norm + 1e-8) + (1 - mask) * v
        
        # Householder matrix: I - 2 * v * v^T
        I = torch.eye(self.embedding_dim, device=z_e.device)
        rotation_matrix = I - 2 * torch.bmm(v.unsqueeze(-1), v.unsqueeze(-2))
        
        return rotation_matrix
    
    def forward(self, z_e):
        """
        Inputs:
        - z_e: output of encoder [B, D]
        
        Returns:
        - q: quantized vectors [B, D]
        - loss: commitment loss
        - perplexity: measure of codebook usage
        - encodings: one-hot encodings of quantized vectors
        """
        # Reshape input
        z_e_flat = z_e.view(-1, self.embedding_dim)
        
        # Compute distances
        distances = torch.sum(z_e_flat ** 2, dim=1, keepdim=True) + \
                    torch.sum(self.embedding.weight ** 2, dim=1) - \
                    2 * torch.matmul(z_e_flat, self.embedding.weight.t())
        
        # Find nearest embedding
        encoding_indices = torch.argmin(distances, dim=1)
        encodings = F.one_hot(encoding_indices, self.num_embeddings).float()
        
        # Quantize
        quantized = self.embedding(encoding_indices)
        
        # Apply rotation if enabled
        if self.use_rotation:
            # Compute rotation matrices for each vector
            rotation_matrices = self.compute_rotation_matrix(z_e_flat, quantized)
            
            # Apply rotation to z_e
            rotated_z_e = torch.bmm(rotation_matrices, z_e_flat.unsqueeze(-1)).squeeze(-1)
            
            # Use rotated z_e for decoder, but keep original quantized for loss
            q_out = rotated_z_e
        else:
            # Standard VQ-VAE: use quantized vectors
            q_out = quantized
        
        # Compute loss
        q_latent_loss = F.mse_loss(q_out.detach(), z_e_flat)
        e_latent_loss = F.mse_loss(q_out, z_e_flat.detach())
        loss = q_latent_loss + self.commitment_cost * e_latent_loss
        
        # Update embeddings with EMA
        if self.training and self.use_ema:
            self.ema_cluster_size = self.ema_decay * self.ema_cluster_size + \
                                   (1 - self.ema_decay) * torch.sum(encodings, dim=0)
            
            # Laplace smoothing
            n = torch.sum(self.ema_cluster_size)
            self.ema_cluster_size = ((self.ema_cluster_size + 1e-5) / 
                                    (n + self.num_embeddings * 1e-5) * n)
            
            # Update weights
            dw = torch.matmul(encodings.t(), z_e_flat)
            self.ema_w = self.ema_decay * self.ema_w + (1 - self.ema_decay) * dw
            
            # Normalize weights
            self.embedding.weight.data = self.ema_w / self.ema_cluster_size.unsqueeze(1)
        
        # Straight-through estimator
        q_out = z_e_flat + (q_out - z_e_flat).detach()
        
        # Reshape to match input
        q_out = q_out.view(z_e.shape)
        
        # Calculate perplexity (measure of codebook usage)
        avg_probs = torch.mean(encodings, dim=0)
        perplexity = torch.exp(-torch.sum(avg_probs * torch.log(avg_probs + 1e-10)))
        
        return q_out, loss, perplexity, encoding_indices

class Encoder(nn.Module):
    """
    Encoder network for VQ-VAE
    """
    def __init__(self, in_channels, hidden_dims, embedding_dim):
        super(Encoder, self).__init__()
        
        modules = []
        for h_dim in hidden_dims:
            modules.append(
                nn.Sequential(
                    nn.Conv2d(in_channels, h_dim, kernel_size=4, stride=2, padding=1),
                    nn.BatchNorm2d(h_dim),
                    nn.LeakyReLU(0.2)
                )
            )
            in_channels = h_dim
        
        modules.append(
            nn.Sequential(
                nn.Conv2d(hidden_dims[-1], embedding_dim, kernel_size=1, stride=1),
                nn.BatchNorm2d(embedding_dim),
                nn.LeakyReLU(0.2)
            )
        )
        
        self.encoder = nn.Sequential(*modules)
    
    def forward(self, x):
        return self.encoder(x)

class Decoder(nn.Module):
    """
    Decoder network for VQ-VAE
    """
    def __init__(self, embedding_dim, hidden_dims, out_channels):
        super(Decoder, self).__init__()
        
        hidden_dims = hidden_dims[::-1]  # Reverse for decoder
        modules = []
        
        modules.append(
            nn.Sequential(
                nn.Conv2d(embedding_dim, hidden_dims[0], kernel_size=1, stride=1),
                nn.BatchNorm2d(hidden_dims[0]),
                nn.LeakyReLU(0.2)
            )
        )
        
        for i in range(len(hidden_dims) - 1):
            modules.append(
                nn.Sequential(
                    nn.ConvTranspose2d(hidden_dims[i], hidden_dims[i + 1], 
                                      kernel_size=4, stride=2, padding=1),
                    nn.BatchNorm2d(hidden_dims[i + 1]),
                    nn.LeakyReLU(0.2)
                )
            )
        
        modules.append(
            nn.Sequential(
                nn.ConvTranspose2d(hidden_dims[-1], out_channels, 
                                  kernel_size=4, stride=2, padding=1),
                nn.Tanh()
            )
        )
        
        self.decoder = nn.Sequential(*modules)
    
    def forward(self, x):
        return self.decoder(x)

class RotatedVQVAE(nn.Module):
    """
    Complete VQ-VAE model with rotation-based vector quantization
    """
    def __init__(self, in_channels=3, hidden_dims=[64, 128, 256], 
                 embedding_dim=256, num_embeddings=8192, 
                 commitment_cost=0.25, use_rotation=True, ema_decay=0.99):
        super(RotatedVQVAE, self).__init__()
        
        self.encoder = Encoder(in_channels, hidden_dims, embedding_dim)
        self.vector_quantizer = VectorQuantizer(num_embeddings, embedding_dim, 
                                               commitment_cost, use_rotation, ema_decay)
        self.decoder = Decoder(embedding_dim, hidden_dims, in_channels)
    
    def forward(self, x):
        z_e = self.encoder(x)
        
        # Permute for vector quantizer
        z_e = z_e.permute(0, 2, 3, 1).contiguous()
        
        # Quantize
        shape = z_e.shape
        z_e_flat = z_e.view(-1, shape[-1])
        q_flat, vq_loss, perplexity, encoding_indices = self.vector_quantizer(z_e_flat)
        q = q_flat.view(shape)
        
        # Permute back for decoder
        q = q.permute(0, 3, 1, 2).contiguous()
        
        # Decode
        reconstructions = self.decoder(q)
        
        return reconstructions, vq_loss, perplexity, encoding_indices 