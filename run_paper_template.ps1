# PowerShell script for running the paper writing agent

# Set the API keys (replace with your own keys)
$env:ANTHROPIC_API_KEY = "your-anthropic-api-key-here"
$env:OPENAI_API_KEY = "your-openai-api-key-here"
$env:GEMINI_API_KEY = "your-gemini-api-key-here"

# Set the research field and instance ID
$research_field = "vq"
$instance_id = "rotated_vq"

# Ensure the vq directory exists
if (-not (Test-Path "$research_field")) {
    Write-Host "Creating directory: $research_field"
    New-Item -ItemType Directory -Force -Path "$research_field" | Out-Null
}

# Ensure templates are properly set up (if using template_manager.py)
Write-Host "Setting up templates for paper writing..."
python template_manager.py $research_field

# Run the paper writing script
Write-Host "Running paper writing script with research_field=$research_field and instance_id=$instance_id..."
python writing.py --research_field $research_field --instance_id $instance_id 

# If the paper writing completed successfully, compile the PDF
if ($LASTEXITCODE -eq 0) {
    Write-Host "Paper sections generated successfully. Compiling PDF..."
    python tex_writer_simplified.py --target_dir "$research_field/target_sections/$instance_id"
}
else {
    Write-Host "Paper writing process failed with exit code $LASTEXITCODE"
} 