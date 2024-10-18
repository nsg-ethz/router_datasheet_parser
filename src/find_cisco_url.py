import os
import re

def find_cisco_url(dir):

    # Define the pattern for matching URLs
    url_pattern = re.compile(r'https?://[^\s]+')
    cisco_with_url = []
    
    # Iterate through all files in the given directory
    for root, _, files in os.walk(dir):
        for file in files:

            file_path = os.path.join(root, file)
            
            # Open and read the file
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Check if the content matches the URL pattern
                if url_pattern.search(content):
                    print(f"URL found in file: {file_path}")
                    cisco_with_url.append(file_path)
    
    return cisco_with_url


if __name__ == "__main__":
    dir = "Cisco/"
    result = find_cisco_url(dir)
    print(result, len(result))