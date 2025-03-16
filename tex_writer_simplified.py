import os
import shutil
import subprocess
import sys
import json
import re

def copy_section_files(target_sections_dir, output_dir):
    """
    Copy LaTeX section files from target_sections directory to the output directory
    
    Args:
        target_sections_dir (str): Path to the directory containing section files
        output_dir (str): Path to the output directory where files will be copied
    
    Returns:
        list: List of copied files
    """
    copied_files = []
    
    # Check if target_sections_dir exists
    if not os.path.exists(target_sections_dir):
        print(f"Target sections directory not found: {target_sections_dir}")
        return copied_files
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Walk through target_sections_dir
    for root, dirs, files in os.walk(target_sections_dir):
        for file in files:
            if file.endswith('.tex'):
                src_path = os.path.join(root, file)
                # Preserve subdirectory structure
                rel_path = os.path.relpath(root, target_sections_dir)
                dst_dir = os.path.join(output_dir, rel_path)
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, file)
                
                # Copy the file
                shutil.copy2(src_path, dst_path)
                copied_files.append(os.path.relpath(dst_path, output_dir))
                print(f"Copied {src_path} to {dst_path}")
    
    return copied_files

def is_pdflatex_installed():
    """
    Check if pdflatex is installed and available in the system PATH
    """
    try:
        subprocess.run(['pdflatex', '--version'], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL, 
                     timeout=3)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def is_bibtex_installed():
    """
    Check if bibtex is installed and available in the system PATH
    """
    try:
        subprocess.run(['bibtex', '--version'], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL, 
                     timeout=3)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        try:
            subprocess.run(['bibtex'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL, 
                        timeout=1)
            return True
        except:
            return False

def is_latexmk_installed():
    """
    Check if latexmk is installed and available in the system PATH
    """
    try:
        subprocess.run(['latexmk', '--version'], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL, 
                     timeout=3)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def create_vscode_settings(project_dir):
    """
    Create VS Code settings for LaTeX Workshop extension
    """
    vscode_dir = os.path.join(project_dir, '.vscode')
    os.makedirs(vscode_dir, exist_ok=True)
    
    settings_file = os.path.join(vscode_dir, 'settings.json')
    
    # Create or update settings.json
    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
    
    # Configure LaTeX Workshop to use pdflatex directly
    settings["latex-workshop.latex.tools"] = [
        {
            "name": "pdflatex",
            "command": "pdflatex",
            "args": [
                "-synctex=1",
                "-interaction=nonstopmode",
                "-file-line-error",
                "%DOC%"
            ]
        },
        {
            "name": "bibtex",
            "command": "bibtex",
            "args": [
                "%DOCFILE%"
            ]
        }
    ]
    
    settings["latex-workshop.latex.recipes"] = [
        {
            "name": "pdflatex",
            "tools": [
                "pdflatex"
            ]
        },
        {
            "name": "pdflatex ➞ bibtex ➞ pdflatex × 2",
            "tools": [
                "pdflatex",
                "bibtex",
                "pdflatex",
                "pdflatex"
            ]
        }
    ]
    
    settings["latex-workshop.latex.recipe.default"] = "pdflatex ➞ bibtex ➞ pdflatex × 2"
    
    # Write settings to file
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=4)
    
    print(f"Created VS Code settings for LaTeX Workshop at {settings_file}")

def run_latex_with_bibtex(main_tex_file):
    """
    Run the full LaTeX compilation sequence with BibTeX
    """
    # Get base filename without extension for bibtex
    base_name = os.path.splitext(main_tex_file)[0]
    
    try:
        # First LaTeX run - generates aux file for BibTeX
        print("First pdflatex run...")
        result1 = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', main_tex_file],
            capture_output=True,
            text=True
        )
        
        # BibTeX run - processes bibliography
        print("Running bibtex...")
        result2 = subprocess.run(
            ['bibtex', base_name],
            capture_output=True,
            text=True
        )
        
        # Log BibTeX output
        print(result2.stdout)
        
        # Two more LaTeX runs to resolve references
        print("Second pdflatex run...")
        result3 = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', main_tex_file],
            capture_output=True,
            text=True
        )
        
        print("Third pdflatex run...")
        result4 = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', main_tex_file],
            capture_output=True,
            text=True
        )
        
        # Check if PDF was generated
        pdf_file = base_name + '.pdf'
        return os.path.exists(pdf_file)
    
    except Exception as e:
        print(f"Compilation error: {str(e)}")
        return False

def check_and_clean_section_files(copied_files, output_dir):
    """
    Remove bibliography commands from section files that might conflict with main document
    """
    bib_commands = [
        '\\bibliographystyle', 
        '\\bibliography', 
        '\\begin{thebibliography}',
        '\\end{thebibliography}'
    ]
    
    for file_path in copied_files:
        full_path = os.path.join(output_dir, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check if file contains bibliography commands
                needs_cleaning = False
                for cmd in bib_commands:
                    if cmd in content:
                        needs_cleaning = True
                        break
                
                if needs_cleaning:
                    print(f"Detected bibliography commands in {file_path}, cleaning...")
                    # Remove lines with bibliography commands
                    lines = content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        if not any(cmd in line for cmd in bib_commands):
                            cleaned_lines.append(line)
                    
                    # Write back the cleaned content
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(cleaned_lines))
                    
                    print(f"Cleaning complete: {file_path}")
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")

def create_basic_tex_file(filename, section_files):
    """
    Create a basic LaTeX file that includes all section files
    """
    with open(filename, 'w') as f:
        f.write("\\documentclass[11pt,a4paper]{article}\n")
        f.write("\\usepackage[utf8]{inputenc}\n")
        f.write("\\usepackage[T1]{fontenc}\n")
        f.write("\\usepackage{graphicx}\n")
        f.write("\\usepackage{amsmath}\n")
        f.write("\\usepackage{amssymb}\n")
        f.write("\\usepackage{booktabs}\n")
        f.write("\\usepackage{hyperref}\n")
        f.write("\\usepackage{natbib}\n")
        f.write("\\usepackage{geometry}\n")
        
        f.write("\\title{Vector Quantization for Neural Networks}\n")
        f.write("\\author{AI Researcher}\n")
        f.write("\\date{\\today}\n")
        f.write("\n")
        f.write("\\begin{document}\n")
        f.write("\\maketitle\n\n")
        
        # Standard paper section order
        section_map = {'abstract': None, 'introduction': None, 'related_work': None, 
                      'methodology': None, 'experiments': None, 'conclusion': None}
        
        # Categorize sections
        for section_file in section_files:
            file_path = os.path.splitext(section_file)[0]
            # Find the section type based on filename
            for key in section_map.keys():
                if key in file_path.lower():
                    section_map[key] = file_path.replace('\\', '/')
                    break
        
        # Add sections in order
        for section_type in section_map:
            if section_map[section_type]:
                f.write(f"\\input{{{section_map[section_type]}}}\n\n")
        
        # Bibliography settings
        f.write("\\bibliographystyle{apalike}\n")
        f.write("\\bibliography{references}\n\n")
        
        f.write("\\end{document}\n")
    
    print(f"Created basic LaTeX file: {filename}")

def compile_latex_project(project_dir, main_tex_file, target_sections_dir=None):
    """
    Main function to compile a LaTeX project
    """
    try:
        # Ensure project directory exists
        os.makedirs(project_dir, exist_ok=True)
        
        # Switch to project directory
        original_dir = os.getcwd()
        os.chdir(project_dir)
        
        # Copy section files if target_sections_dir is provided
        copied_files = []
        if target_sections_dir and os.path.exists(target_sections_dir):
            print(f"Copying section files from {target_sections_dir} to {project_dir}")
            copied_files = copy_section_files(target_sections_dir, project_dir)
            print(f"Copied {len(copied_files)} files")
            
            # Clean bibliography commands
            check_and_clean_section_files(copied_files, project_dir)
        
        # Create main.tex if it doesn't exist
        if not os.path.exists(main_tex_file):
            create_basic_tex_file(main_tex_file, copied_files)
        
        # Create VS Code configuration
        create_vscode_settings(project_dir)
        
        # Check for LaTeX tools
        pdflatex_available = is_pdflatex_installed()
        bibtex_available = is_bibtex_installed()
        latexmk_available = is_latexmk_installed()
        
        if not pdflatex_available:
            print("Warning: pdflatex is not installed. Cannot compile document.")
            return False
            
        if not bibtex_available:
            print("Warning: bibtex is not installed. Bibliography won't be processed.")
        
        if not latexmk_available:
            print("Warning: latexmk is not installed. LaTeX Workshop extension may not work properly.")
            print("But pdflatex is available, will compile directly with pdflatex.")
        
        # Compile document
        print(f"Starting compilation: {os.path.join(project_dir, main_tex_file)}")
        print("Using complete compilation sequence: pdflatex → bibtex → pdflatex → pdflatex")
        
        if run_latex_with_bibtex(main_tex_file):
            pdf_file = os.path.splitext(main_tex_file)[0] + '.pdf'
            print(f"PDF generated successfully: {os.path.join(project_dir, pdf_file)}")
            return True
        else:
            print("PDF generation failed")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
        
    finally:
        # Restore original working directory
        os.chdir(original_dir)

if __name__ == "__main__":
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set output and input directories
    project_directory = os.path.join(script_dir, "tex_output")
    main_file = "main.tex"
    target_sections = os.path.join(script_dir, "vq", "target_sections")
    
    # Try alternative paths if the primary one doesn't exist
    if not os.path.exists(target_sections):
        target_sections = os.path.abspath("paper_agent/vq/target_sections")
        if not os.path.exists(target_sections):
            target_sections = os.path.join(os.path.dirname(script_dir), "vq", "target_sections")
    
    print(f"Project directory: {project_directory}")
    print(f"Target section directory: {target_sections}")
    
    if not os.path.exists(target_sections):
        print(f"Warning: Target section directory not found: {target_sections}")
        sys.exit(1)
    
    # Run the compilation process
    compile_latex_project(project_directory, main_file, target_sections) 