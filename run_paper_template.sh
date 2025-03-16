#!/bin/bash
# Bash script for running the paper writing agent on Ubuntu/macOS

# Set the API keys (replace with your own keys)
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export OPENAI_API_KEY="your-openai-api-key-here"
export GEMINI_API_KEY="your-gemini-api-key-here"

# Set the research field and instance ID
research_field="vq"
instance_id="rotated_vq"

# Ensure the research field directory exists
if [ ! -d "$research_field" ]; then
    echo "Creating directory: $research_field"
    mkdir -p "$research_field"
fi

# Ensure templates are properly set up (if using template_manager.py)
echo "Setting up templates for paper writing..."
python template_manager.py $research_field

# Run the paper writing script
echo "Running paper writing script with research_field=$research_field and instance_id=$instance_id..."
python writing.py --research_field $research_field --instance_id $instance_id 

# If the paper writing completed successfully, compile the PDF
if [ $? -eq 0 ]; then
    echo "Paper sections generated successfully. Compiling PDF..."
    python tex_writer_simplified.py --target_dir "$research_field/target_sections/$instance_id"
else
    echo "Paper writing process failed with exit code $?"
fi 