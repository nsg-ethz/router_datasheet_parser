import yaml
import csv
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
    Save the result to a yaml file

    Parameters:
        data:       The content which will be stored to the yaml file
        file_path:  The path of the yaml which will store the content
    """
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_prompt_components(file_path, router_name):
    
    with open(file_path, "r") as file:
        lines = file.readlines()

    # Parse components from the file
    components = {"PERSONA": "", "HIGH_LEVEL_TASK": "", "LOW_LEVEL_TASK": ""}
    current_key = None

    for line in lines:
        line = line.strip()
        if line in components:
            current_key = line
        elif current_key:
            components[current_key] += line + "\n"
    
    # Format the LOW_LEVEL_TASK with the router_name
    components["LOW_LEVEL_TASK"] = components["LOW_LEVEL_TASK"].format(router_name=router_name)

    return components
