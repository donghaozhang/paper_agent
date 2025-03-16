import os
import shutil
import subprocess
import sys
import json
import zipfile
from datetime import datetime
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
    
    Returns:
        bool: True if pdflatex is installed, False otherwise
    """
    try:
        # Use subprocess.run with a timeout to avoid hanging
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
    
    Returns:
        bool: True if bibtex is installed, False otherwise
    """
    try:
        # Use subprocess.run with a timeout to avoid hanging
        subprocess.run(['bibtex', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      timeout=3)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        # Try to detect MiKTeX installation, which might not respond to version flag
        try:
            subprocess.run(['bibtex'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL, 
                        timeout=1)
            return True
        except:
            return False

def is_perl_installed():
    """
    Check if perl is installed and available in the system PATH
    
    Returns:
        bool: True if perl is installed, False otherwise
    """
    try:
        # Use subprocess.run with a timeout to avoid hanging
        subprocess.run(['perl', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      timeout=3)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def is_latexmk_installed():
    """
    Check if latexmk is installed and available in the system PATH,
    and also check if perl is installed (required for latexmk)
    
    Returns:
        bool: True if latexmk is installed and usable, False otherwise
    """
    try:
        # First check if perl is installed (required for latexmk)
        if not is_perl_installed():
            return False
            
        # Use subprocess.run with a timeout to avoid hanging
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
    
    Args:
        project_dir (str): Path to the project directory
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
            # If JSON is invalid, start with empty settings
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

def create_zip_for_overleaf(project_dir, main_tex_file):
    """
    Create a ZIP file suitable for uploading to Overleaf
    
    Args:
        project_dir (str): Path to the project directory
        main_tex_file (str): Name of the main tex file
        
    Returns:
        str: Path to the created ZIP file
    """
    try:
        # Create timestamp version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = os.path.join(project_dir, f"overleaf_project_{timestamp}.zip")
        
        # Create ZIP file
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all files in the project directory
            for root, dirs, files in os.walk(project_dir):
                # Exclude .vscode directory and ZIP files
                if '.vscode' in root:
                    continue
                    
                for file in files:
                    # Exclude existing ZIP files and non-essential files
                    if file.endswith('.zip') or file.endswith('.log') or file.endswith('.aux'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    # Get relative path to maintain directory structure
                    rel_path = os.path.relpath(file_path, project_dir)
                    # Add file to ZIP
                    zipf.write(file_path, rel_path)
                    
            # Ensure main.tex is in the root directory
            if not os.path.exists(os.path.join(project_dir, main_tex_file)):
                # If main.tex isn't in the root directory, it might be in a subdirectory, need to copy to root
                found = False
                for root, _, files in os.walk(project_dir):
                    if main_tex_file in files:
                        found = True
                        src_path = os.path.join(root, main_tex_file)
                        with open(src_path, 'r') as f:
                            content = f.read()
                        # Add main.tex to the root of the ZIP
                        zipf.writestr(main_tex_file, content)
                        break
                
                if not found:
                    print(f"Warning: Could not find {main_tex_file}, ZIP may not work properly in Overleaf")
        
        print(f"Created Overleaf project ZIP file: {zip_filename}")
        print(f"You can upload this ZIP file to Overleaf (https://www.overleaf.com/project) for online editing and compilation.")
        return zip_filename
        
    except Exception as e:
        print(f"Error creating ZIP file: {str(e)}")
        return None

def run_latex_with_bibtex(main_tex_file):
    """
    Run the full LaTeX compilation sequence with BibTeX for bibliography generation
    
    Args:
        main_tex_file (str): Name of the main TeX file (without path)
    
    Returns:
        bool: True if compilation was successful, False otherwise
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
        
        # Check if pdflatex was successful
        if result1.returncode != 0:
            print("First pdflatex run failed:")
            if result1.stderr:
                print(result1.stderr)
            error_lines = re.findall(r'!.*', result1.stdout)
            if error_lines:
                print("\nCritical errors:")
                for line in error_lines[:5]:
                    print(line)
            return False
        
        # Before running BibTeX, check if the aux file has multiple bibliography style commands
        # and fix it if necessary
        try:
            aux_file = base_name + '.aux'
            if os.path.exists(aux_file):
                with open(aux_file, 'r', encoding='utf-8', errors='ignore') as f:
                    aux_content = f.read()
                
                # Check for multiple \bibstyle commands
                bibstyle_count = aux_content.count('\\bibstyle{')
                if bibstyle_count > 1:
                    print(f"Found multiple \\bibstyle commands ({bibstyle_count}). Fixing aux file...")
                    
                    # Keep only the first occurrence of \bibstyle and \bibdata
                    lines = aux_content.split('\n')
                    seen_bibstyle = False
                    seen_bibdata = False
                    fixed_lines = []
                    
                    for line in lines:
                        if '\\bibstyle{' in line:
                            if not seen_bibstyle:
                                fixed_lines.append(line)
                                seen_bibstyle = True
                        elif '\\bibdata{' in line:
                            if not seen_bibdata:
                                fixed_lines.append(line)
                                seen_bibdata = True
                        else:
                            fixed_lines.append(line)
                    
                    # Write back the fixed aux file
                    with open(aux_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(fixed_lines))
                    
                    print("Aux file fixed.")
        except Exception as e:
            print(f"Error fixing aux file: {str(e)}")
            # Continue anyway, as BibTeX might still work
        
        # BibTeX run - processes bibliography
        print("Running bibtex...")
        result2 = subprocess.run(
            ['bibtex', base_name],
            capture_output=True,
            text=True
        )
        
        # Log BibTeX output
        print(result2.stdout)
        
        # Even if bibtex has warnings, continue with pdflatex
        if result2.returncode != 0:
            print("BibTeX warnings (continuing process):")
            if result2.stderr:
                print(result2.stderr)
        
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
        
        # Check final run for errors
        if result4.returncode != 0:
            print("Final pdflatex run failed:")
            if result4.stderr:
                print(result4.stderr)
            error_lines = re.findall(r'!.*', result4.stdout)
            if error_lines:
                print("\nCritical errors:")
                for line in error_lines[:5]:
                    print(line)
            return False
        
        return True
    
    except Exception as e:
        print(f"Compilation error: {str(e)}")
        return False

def compile_latex_project(project_dir, main_tex_file, target_sections_dir=None):
    """
    Compile a LaTeX project containing multiple files
    
    Args:
        project_dir (str): Path to the project directory
        main_tex_file (str): Name of the main tex file
        target_sections_dir (str, optional): Directory containing target section files
    """
    try:
        # Ensure project directory exists
        os.makedirs(project_dir, exist_ok=True)
        
        # Switch to project directory
        original_dir = os.getcwd()
        os.chdir(project_dir)
        
        # If target_sections_dir is provided, copy section files
        copied_files = []
        if target_sections_dir and os.path.exists(target_sections_dir):
            print(f"Copying section files from {target_sections_dir} to {project_dir}")
            copied_files = copy_section_files(target_sections_dir, project_dir)
            print(f"Copied {len(copied_files)} files")
            
            # Check and clean section files for bibliography commands
            check_and_clean_section_files(copied_files, project_dir)
        
        # Ensure main_tex_file exists, create a basic tex file if it doesn't
        if not os.path.exists(main_tex_file):
            create_basic_tex_file(main_tex_file, copied_files)
            print(f"LaTeX file created successfully: {os.path.join(project_dir, main_tex_file)}")
        
        # Get full path to main file
        main_file_path = os.path.join(project_dir, main_tex_file)
        
        # Create VS Code configuration
        create_vscode_settings(project_dir)
        
        # Check if pdflatex, bibtex, and latexmk are installed
        pdflatex_available = is_pdflatex_installed()
        bibtex_available = is_bibtex_installed()
        latexmk_available = is_latexmk_installed()
        perl_available = is_perl_installed()
        
        # Check if references.bib exists, create if not
        if not os.path.exists('references.bib'):
            print("Creating default references.bib file...")
            with open('references.bib', 'w', encoding='utf-8') as f:
                f.write("% Reference file\n")
                f.write("@article{straightthrough,\n")
                f.write("  title={Estimating or Propagating Gradients Through Stochastic Neurons for Conditional Computation},\n")
                f.write("  author={Bengio, Yoshua and L{\\'{e}}onard, Nicholas and Courville, Aaron},\n")
                f.write("  journal={arXiv preprint arXiv:1308.3432},\n")
                f.write("  year={2013}\n")
                f.write("}\n\n")
        
        if not pdflatex_available:
            print(f"Warning: pdflatex is not installed or not in system path.")
            print(f"Cannot compile LaTeX files. Please install TeX Live, MiKTeX, or another LaTeX distribution.")
            print(f"LaTeX files have been successfully created at: {main_file_path}")
            
            # Create ZIP file for Overleaf
            zip_path = create_zip_for_overleaf(project_dir, main_tex_file)
            
            print("\nInstallation Guide:")
            print("1. Download and install MiKTeX: https://miktex.org/download")
            print("2. Select 'Install missing packages' option during installation")
            print("3. Restart your computer after installation")
            print("4. Compile using VS Code's LaTeX Workshop extension, or run this script again")
            print("\nAlternatively:")
            print(f"- Use the created ZIP file ({os.path.basename(zip_path)}) to upload to Overleaf")
            print("- Go to https://www.overleaf.com/project and click 'New Project'")
            print("- Select 'Upload Project' and upload the ZIP file")
            return False
            
        if not bibtex_available:
            print(f"Warning: bibtex is not installed or not in system path.")
            print(f"Will compile with pdflatex, but without bibliography processing.")
        
        if not perl_available and latexmk_available:
            print(f"Warning: Perl is not installed. latexmk requires Perl to run.")
            print(f"Will compile directly with pdflatex.")
            latexmk_available = False
        elif not latexmk_available:
            print(f"Warning: latexmk is not installed. LaTeX Workshop extension may not work properly.")
            print(f"But pdflatex is available, will compile directly with pdflatex.")
        
        print(f"Starting compilation: {main_file_path}")
        
        # Try to compile using latexmk (used by VS Code LaTeX Workshop)
        if latexmk_available:
            try:
                print("Compiling with latexmk (automatically handles references)...")
                result = subprocess.run(
                    ['latexmk', '-pdf', '-interaction=nonstopmode', main_tex_file],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("latexmk compilation successful")
                    compile_success = True
                else:
                    print(f"latexmk compilation error, trying pdflatex+bibtex:")
                    # Check if error messages contain Perl-related errors
                    if "perl" in result.stdout.lower() or "perl" in result.stderr.lower():
                        print("Detected Perl-related errors. latexmk requires Perl to run.")
                    # If latexmk fails, fall back to pdflatex+bibtex
                    compile_success = False
            except Exception as e:
                print(f"latexmk execution error: {str(e)}")
                print("Trying pdflatex and bibtex")
                compile_success = False
        else:
            compile_success = False
            
        # If latexmk is not available or failed, use pdflatex+bibtex
        if not compile_success:
            if bibtex_available:
                print("Using complete compilation sequence: pdflatex → bibtex → pdflatex → pdflatex")
                compile_success = run_latex_with_bibtex(main_tex_file)
            else:
                print("Using only pdflatex for compilation (no bibliography processing)")
                # Run compilation command twice (for table of contents and references)
                for i in range(2):
                    result = subprocess.run(
                        ['pdflatex', '-interaction=nonstopmode', main_tex_file],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        print(f"Compilation error:")
                        if result.stderr:
                            print(result.stderr)
                        # Extract key error information from stdout
                        error_lines = re.findall(r'!.*', result.stdout)
                        if error_lines:
                            print("\nCritical errors:")
                            for line in error_lines[:5]:  # Only show first 5 errors
                                print(line)
                            compile_success = False
                            break
                        compile_success = True
        
        # Check if PDF was generated
        pdf_file = os.path.splitext(main_tex_file)[0] + '.pdf'
        if os.path.exists(pdf_file) and compile_success:
            print(f"PDF generated successfully: {os.path.join(project_dir, pdf_file)}")
            # Check if file has undefined references
            aux_file = os.path.splitext(main_tex_file)[0] + '.aux'
            if os.path.exists(aux_file):
                with open(aux_file, 'r', encoding='utf-8', errors='ignore') as f:
                    aux_content = f.read()
                    if "undefined" in aux_content or "Undefined" in aux_content:
                        print("Warning: Document has undefined references. Try running the compilation sequence again to resolve.")
            return True
        else:
            print("PDF generation failed")
            return False
            
    except Exception as e:
        print(f"Compilation error: {str(e)}")
        return False
        
    finally:
        # Restore original working directory
        os.chdir(original_dir)

def create_basic_tex_file(filename, section_files):
    """
    Create a basic LaTeX file, containing all section files
    
    Args:
        filename (str): Name of the LaTeX file to create
        section_files (list): List of section files to include
    """
    with open(filename, 'w') as f:
        f.write("\\documentclass[11pt,a4paper]{article}\n")
        f.write("\\usepackage[utf8]{inputenc}\n")
        f.write("\\usepackage[T1]{fontenc}\n")
        f.write("\\usepackage{graphicx}\n")
        f.write("\\usepackage{amsmath}\n")
        f.write("\\usepackage{amssymb}\n")
        f.write("\\usepackage{booktabs}\n")
        f.write("\\usepackage[expansion=false]{microtype}\n")
        f.write("\\usepackage{hyperref}\n")
        f.write("\\usepackage{natbib}\n")
        f.write("\\usepackage{geometry}\n")
        f.write("\\usepackage{array}\n")
        f.write("\\usepackage{parskip}\n")
        f.write("\\usepackage{float}\n")
        f.write("\n")
        f.write("% Better spacing\n")
        f.write("\\geometry{margin=1in}\n")
        f.write("\\setlength{\\parindent}{0pt}\n")
        f.write("\\setlength{\\parskip}{1em}\n")
        f.write("\n")
        f.write("% Float settings - prevent \"too many unprocessed floats\"\n")
        f.write("\\renewcommand{\\topfraction}{0.9}\n")
        f.write("\\renewcommand{\\bottomfraction}{0.8}\n")
        f.write("\\renewcommand{\\textfraction}{0.07}\n")
        f.write("\\renewcommand{\\floatpagefraction}{0.7}\n")
        f.write("\\setcounter{topnumber}{3}\n")
        f.write("\\setcounter{bottomnumber}{2}\n")
        f.write("\\setcounter{totalnumber}{5}\n")
        f.write("\n")
        f.write("% Hyperref settings\n")
        f.write("\\hypersetup{\n")
        f.write("    colorlinks=true,\n")
        f.write("    linkcolor=blue,\n")
        f.write("    filecolor=magenta,\n")
        f.write("    citecolor=blue,\n")
        f.write("    urlcolor=cyan\n")
        f.write("}\n")
        f.write("\n")
        
        # Try to extract a title from section files
        paper_title = "Vector Quantization for Neural Networks"
        try:
            # Look for a title in abstract or introduction
            for section_file in section_files:
                if 'abstract' in section_file.lower() or 'introduction' in section_file.lower():
                    section_path = os.path.join(os.getcwd(), section_file)
                    if os.path.exists(section_path):
                        with open(section_path, 'r', encoding='utf-8', errors='ignore') as sf:
                            content = sf.read(1000)  # Read first 1000 chars
                            # Try to find potential title
                            matches = re.findall(r'[A-Z][A-Za-z\s:]{10,50}', content)
                            if matches:
                                paper_title = matches[0].strip()
                                break
        except Exception:
            # If any error occurs, use default title
            pass
        
        f.write(f"\\title{{\\Large{{\\textbf{{{paper_title}}}}}}}\n")
        f.write("\\author{AI Researcher}\n")
        f.write("\\date{\\today}\n")
        f.write("\n")
        f.write("\\begin{document}\n")
        f.write("\\maketitle\n\n")
        
        # Standard paper section order
        ordered_sections = []
        section_map = {'abstract': None, 'introduction': None, 'related_work': None, 
                      'methodology': None, 'method': None, 'experiments': None, 
                      'results': None, 'conclusion': None, 'discussion': None}
        
        # First pass: categorize sections
        for section_file in section_files:
            file_path = os.path.splitext(section_file)[0]
            # Find the section type based on filename
            section_type = 'other'
            for key in section_map.keys():
                if key in file_path.lower():
                    section_type = key
                    section_map[key] = file_path.replace('\\', '/')
                    break
            
            if section_type == 'other':
                ordered_sections.append(file_path.replace('\\', '/'))
        
        # Second pass: add sections in order
        if section_map['abstract']:
            f.write(f"\\input{{{section_map['abstract']}}}\n\n")
        
        if section_map['introduction']:
            f.write(f"\\input{{{section_map['introduction']}}}\n\n")
            
        if section_map['related_work']:
            f.write(f"\\input{{{section_map['related_work']}}}\n\n")
        
        if section_map['methodology'] or section_map['method']:
            method_section = section_map['methodology'] if section_map['methodology'] else section_map['method']
            if method_section:
                f.write(f"\\input{{{method_section}}}\n\n")
        
        if section_map['experiments'] or section_map['results']:
            exp_section = section_map['experiments'] if section_map['experiments'] else section_map['results']
            if exp_section:
                f.write(f"\\input{{{exp_section}}}\n\n")
        
        if section_map['conclusion'] or section_map['discussion']:
            conc_section = section_map['conclusion'] if section_map['conclusion'] else section_map['discussion']
            if conc_section:
                f.write(f"\\input{{{conc_section}}}\n\n")
        
        # Add any remaining sections
        for section in ordered_sections:
            f.write(f"\\input{{{section}}}\n\n")
        
        if not section_files:
            f.write("\\section{Empty Document}\n")
            f.write("This document is currently empty.\n")
        
        # Move the bibliography style outside of any included files to avoid conflicts
        # We'll set it here explicitly
        f.write("% Bibliography settings\n")
        f.write("\\bibliographystyle{apalike}\n")
        f.write("\\bibliography{references}\n\n")
        
        f.write("\\end{document}\n")
    
    print(f"Created basic LaTeX file: {filename}")

# Also check if any section files contain bibliography commands and remove them
def check_and_clean_section_files(copied_files, output_dir):
    """
    Check section files for bibliography commands that might conflict with main document
    
    Args:
        copied_files (list): List of copied section files 
        output_dir (str): Output directory containing the files
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

# Usage example
if __name__ == "__main__":
    # Use relative path to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create project directory (in paper_agent's tex_output file)
    project_directory = os.path.join(script_dir, "tex_output")
    
    # Set main file name and target_sections directory
    main_file = "main.tex"
    
    # First try relative path to the script
    target_sections = os.path.join(script_dir, "vq", "target_sections")
    
    # If above path doesn't exist, try other possible paths
    if not os.path.exists(target_sections):
        # Try relative path to current working directory
        target_sections = os.path.abspath("paper_agent/vq/target_sections")
        
        # If above path still doesn't exist, try upper directory
        if not os.path.exists(target_sections):
            target_sections = os.path.join(os.path.dirname(script_dir), "vq", "target_sections")
    
    print(f"Project directory: {project_directory}")
    print(f"Target section directory: {target_sections}")
    
    if not os.path.exists(target_sections):
        print(f"Warning: Target section directory not found: {target_sections}")
        sys.exit(1)
    
    # Execute compilation
    compile_latex_project(project_directory, main_file, target_sections)