import os

def collect_code_files(base_directory: str, output_file: str):
    """
    Collects all .py and .toml files from the base directory and writes their contents 
    to a single output text file, each preceded by the file path as a comment.
    """
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Walk through the base directory
        for root, _, files in os.walk(base_directory):
            for file in files:
                if file.endswith('.py') or file.endswith('.md') or file.endswith('.sql') or file.endswith('.json') or file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    
                    # Write the file path as a comment
                    outfile.write(f"# {file_path}\n\n")
                    
                    # Read the file content
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                    
                    # Write the content to the output file
                    outfile.write(content)
                    outfile.write("\n\n" + "-"*80 + "\n\n")  # Separator between files

                    print(f"Processed file: {file_path}")

if __name__ == '__main__':
    # Use the current directory as the base directory
    base_directory = os.getcwd()  # Change this if you want a different directory
    
    # Define the output file name
    output_file = 'all_code_files.txt'
    
    # Collect the code files and write to the output file
    collect_code_files(base_directory, output_file)
    print(f"All files collected into {output_file}")
