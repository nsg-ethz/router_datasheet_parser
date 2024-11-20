import yaml
import csv
import json
import pdfplumber
import os
import subprocess
import pandas as pd


def record_without_url_csv(file_path, manufacturer, model, write_header=False):
    """
    In the netbox dataset, some router lacks url information,
    while the url is of great importance for the LLM analysis.
    Those routers without url shall be recorded.

    Parameters:
        file_path:      The file path where the record will be stored
        manufactuere:   The vendor of a router, e.g., Cisco
        model:          The router model, e.g., APIC-M3
        write_header:   Write the header of this csv, namely 'manufacturer' and 'model'
    """

    mode = "w" if write_header else "a"
    with open(file_path, mode=mode, newline="") as routers_without_url:
        writer = csv.writer(routers_without_url)
        if write_header:
            writer.writerow(["manufacturer", "model"])
        else:
            writer.writerow([manufacturer, model])


def is_model_without_url(model, routers_without_url_csv):
    """
    Judge if this router model contains a URL link

    Parameters:
        model:  The router model
        routers_without_url_csv:    The csv file which contains the routers without a URL
    """
    df = pd.read_csv(routers_without_url_csv)
    return model in df["model"].values


def load_yaml(file_path):
    """
    Load the yaml file

    Parameters:
        file_path:  The path of the yaml file
    """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def save_yaml(data, file_path):
    """
    Save the result to a yaml file.

    Parameters:
        data:       The content which will be stored to the yaml file.
        file_path:  The path of the yaml which will store the content.
    """
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(file_path):
    """
    Load json file and store the content inside into a variable

    Parameter:
        file_path:  The path of a file
    """
    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    return data


def save_json(data, file_path):
    """
    Save the content into a json file.

    Parameters:
        data:       The data waiting to be stored in the json file.
        file_path:  The file which will be used to store the data.
    """
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def load_prompt_components(file_path, router_info):
    """
    Some long LLM prompts are store in a text file.
    This function will load the prompt and return it to LLM.

    Parameters:
        file_path:      The path of a file.
        router_info:    The router info giving to the LLM prompt.
    
    Returns:
        The complete prompt to the LLM.
    """
    with open(file_path, "r") as file:
        lines = file.readlines()

    components = {"PERSONA": "", "HIGH_LEVEL_TASK": "", "LOW_LEVEL_TASK": ""}
    current_key = None

    for line in lines:
        line = line.strip()
        if line in components:
            current_key = line
        elif current_key:
            components[current_key] += line + "\n"

    components["LOW_LEVEL_TASK"] = components["LOW_LEVEL_TASK"].format(router_info=router_info)

    return components


def pdf_to_markdown(url, router_name):
    """
    Transfer the pdf url link to md

    Parameters:
        url:            The pdf url.
        router_name:    The name of a router.
    
    Returns:
        A md file transferred from the pdf url if succeeds,
        otherwise, return None
    """

    print("url : ", url)

    # Step 1: Define paths
    output_dir = "../markdown"
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{router_name}.pdf") # The key of step 1 is to get the pdf_path
    output_md_file = os.path.join(output_dir, f"{router_name}.md")

    # Step 2: Download PDF from the URL with error handling
    command = ["curl", "-o", pdf_path, url]
    try:
        subprocess.run(command, check=True)
        print(f"Downloaded: {pdf_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to download. Error: {e}")

    # Step 3: Extract text from the PDF
    pdf_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pdf_text += page_text + "\n"
        print("Extracted text from PDF.")
    except Exception as e:
        print(f"Failed to extract text from PDF {pdf_path}: {e}")
        return None

    # Step 4: Save the text as a Markdown file
    try:
        with open(output_md_file, "w") as md_file:
            md_file.write("# PDF to Markdown Conversion\n\n")
            md_file.write(pdf_text)
        print(f"Saved Markdown to {output_md_file}")
    except IOError as e:
        print(f"Failed to write Markdown file {output_md_file}: {e}")
        return None

    # Step 5: Load Markdown content into a variable
    try:
        with open(output_md_file, "r") as md_file:
            markdown_content = md_file.read()
        print("Loaded Markdown content into variable.")
    except IOError as e:
        print(f"Failed to read Markdown file {output_md_file}: {e}")
        return None

    return markdown_content
