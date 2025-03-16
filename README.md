# Paper Agent

A framework for automated academic paper writing using AI agents and templates.

## Overview

Paper Agent uses specialized AI agents to compose research papers by generating different sections (introduction, methodology, experiments, results, etc.) in a structured manner. It supports multiple research fields and manages the complete paper generation process.

## Features

- Multi-agent system for collaborative paper writing
- Support for different research fields (VQ, GNN, Diffusion, etc.)
- Template-based section generation
- LaTeX output for professional papers
- Checkpoint system to save progress

## Usage

1. Set up API keys in a custom PowerShell script:

```powershell
# Example: run_paper_custom.ps1
$env:ANTHROPIC_API_KEY = "your-anthropic-key"
$env:OPENAI_API_KEY = "your-openai-key"
$env:GEMINI_API_KEY = "your-gemini-key"

# Set the research field and instance ID
$research_field = "vq"  # Options: vq, gnn, rec, diffu_flow
$instance_id = "rotated_vq"

# Run the paper writing script
python writing.py --research_field $research_field --instance_id $instance_id
```

2. Run the script:

```
./run_paper_custom.ps1
```

## Project Structure

- `writing.py`: Main entry point that coordinates writing all sections
- Section composition modules:
  - `methodology_composing_using_template.py`
  - `related_work_composing_using_template.py`
  - `experiments_composing.py`
  - `introduction_composing.py`
  - `conclusion_composing.py`
  - `abstract_composing.py`
- `tex_output/`: Generated LaTeX files and compiled PDFs
- `[research_field]/[instance_id]/`: Project-specific files
  - `cache_1/agents/`: Agent configurations and outputs
  - `workplace/`: Working directory for paper generation

## Requirements

- Python 3.8+
- LaTeX distribution (for PDF compilation)
- API keys for Anthropic Claude, OpenAI, and Google Gemini

## License

MIT
