import os
from tqdm import tqdm
from collections import OrderedDict
from load_file import *


def merge_dicts(dict1, dict2):
    """
    Merge two dictionaries into one. Specifically in the case of two same keys:
    1. If the two values are also the same: It even verify our confidence of this value is more than perfect.
    2. If the one of the values is null: Overwrite null with the non-null value.
    
    Parameters:
        dict1:  The first dictionary
        dict2:  The second dictionary
    """
    for key, value in dict2.items():
        # If the key exists in both dictionaries
        if key in dict1:
            if isinstance(value, dict) and isinstance(dict1[key], dict):
                merge_dicts(dict1[key], value)
            # If both values are non-null and different, combine them as "value 1 and value 2"
            elif value and dict1[key] and value != dict1[key]:
                dict1[key] = f"{dict1[key]} and {value}"
            # If one of the values is null, use the non-null value
            elif not dict1[key]:
                dict1[key] = value
        else:
            # If key only exists in dict2, add it to dict1
            dict1[key] = value


def organize_dicts(data):
    """
    Organize the dictionary into the format that we want
    
    Parameters:
        data:   The dictionary data waiting to be organized
    
    Returns:
        organized_data: The organized dictionary data in the format that we want
    """
    organized_data = OrderedDict([
        ("manufacturer", data["manufacturer"]),
        ("model", data["model"]),
        ("slug", data["slug"]),
        ("part_number", data["part_number"]),
        ("u_height", data["u_height"]),
        ("router_type", data["router_type"]),
        ("datasheet_url", data["datasheet_url"]),
        ("datasheet_pdf", data["datasheet_pdf"]),
        ("release_date", data["release_date"]),
        ("end_of_sale", data["end_of_sale"]),
        ("end_of_support", data["end_of_support"]),
        ("max_throughput", data["max_throughput"]),
        ("max_power_draw", data["max_power_draw"]),
        ("typical_power_draw", data["typical_power_draw"]),
        ("psu", data["psu"]),
    ])

    return dict(organized_data)


if __name__ == "__main__":

    result_directory = "../result/Cisco/"
    routers_without_url = "../result/routers_without_url.csv"
    # router_names = [name for name in os.listdir(result_directory) if os.path.isdir(os.path.join(result_directory, name))]
    router_names = ["ASR-9006", "Meraki MR42", "SG350XG-24T", "Catalyst 9115AXI-E"]

    for router_name in tqdm(router_names):
        if not is_model_without_url(router_name, routers_without_url):

            filtered_netbox_file = result_directory + router_name + f"/{router_name}_filtered_netbox.yaml"
            url_llm_file = result_directory + router_name + f"/{router_name}_url_llm.yaml"
            date_file = result_directory + router_name + f"/{router_name}_date_llm.yaml"
            type_file = result_directory + router_name + f"/{router_name}_type_llm.yaml"

            # Load each file
            filtered_netbox_data = load_yaml(filtered_netbox_file)
            url_llm_data = load_yaml(url_llm_file)
            date_data = load_yaml(date_file)
            type_data = load_yaml(type_file)

            # Begin to merge the data
            merged_data = {
                "manufacturer": None,
                "model": None,
                "slug": None,
                "part_number": None,
                "u_height": None,
                "router_type": None,
                "datasheet_url": None,
                "datasheet_pdf": None,
                "release_date": None,
                "end_of_sale": None,
                "end_of_support": None,
                "max_throughput": None,
                "max_power_draw": None,
                "typical_power_draw": None,
                "psu": None,
            }
            merge_dicts(merged_data, filtered_netbox_data)
            merge_dicts(merged_data, url_llm_data)
            merge_dicts(merged_data, date_data)
            merge_dicts(merged_data, type_data)
            
            organzed_data = organize_dicts(merged_data)
            output_file = f"{router_name}_merged.yaml"
            save_yaml(organzed_data, result_directory + router_name + "/" + output_file)

        #TODO: Handle the data without the URL