import os
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
    
    return dict1


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
        ("series", data["series"]),
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
        ("is_poe_capable", data["is_poe_capable"]),
        ("max_poe_draw", data["max_poe_draw"]),
        ("psu", data["psu"]),
    ])

    return dict(organized_data)


def all_files_exist(files):
    """
    Check if all files in the list exist.

    Parameters:
        files (list): List of file paths to check.

    Returns:
        bool: True if all files exist, False if any file is missing.
    """
    return all(os.path.isfile(file) for file in files)


if __name__ == "__main__":

    result_dir = "../result/"

    for manufacturer in os.listdir(result_dir):

        if (manufacturer == "arista") or (manufacturer == "juniper"):
            continue
        
        manufacturer_dir = os.path.join(result_dir, manufacturer)
        throughput_count = 0

        for series_dir in os.listdir(manufacturer_dir):

            series_folder = os.path.join(manufacturer_dir, series_dir)

            for root, dirs, files in os.walk(series_folder):

                for router_dir in dirs:

                    general_data = load_yaml(os.path.join(series_folder, router_dir, "general_llm.yaml"))
                    date_data = load_yaml(os.path.join(series_folder, router_dir, "date_llm.yaml"))

                    # Check if max_throughput exists
                    if (general_data.get("max_throughput") and general_data["max_throughput"].get("value") and date_data.get("release_date")) or \
                        (general_data.get("max_power_draw") and general_data.get("max_power_draw").get("value") and date_data.get("release_date")):
                            
                            print("router_dir: ", router_dir)
                            filtered_netbox_data = load_yaml(os.path.join(series_folder, router_dir, "filtered_netbox.yaml"))
                            type_data = load_yaml(os.path.join(series_folder, router_dir, "type_llm.yaml"))

                            merged_data = {"manufacturer": None, "series": None, "model": None, "slug": None, "part_number": None, "u_height": None,
                                           "router_type": None, "datasheet_url": None, "datasheet_pdf": None, 
                                           "release_date": None, "end_of_sale": None, "end_of_support": None,
                                           "max_throughput": None, "max_power_draw": None, "typical_power_draw": None, 
                                           "is_poe_capable": None, "max_poe_draw": None, "psu": None}
                            
                            merge_dicts(merged_data, filtered_netbox_data)
                            merge_dicts(merged_data, general_data)
                            merge_dicts(merged_data, date_data)
                            merge_dicts(merged_data, type_data)

                            organzed_data = organize_dicts(merged_data)
                            output_file = os.path.join(series_folder, router_dir, "merged.yaml")
                            save_yaml(organzed_data, output_file)
