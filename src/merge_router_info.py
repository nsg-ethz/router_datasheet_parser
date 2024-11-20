import os
from collections import OrderedDict
from load_file import *


def merge_dicts(dict1, dict2, overwrite=False):
    """
    Merge two dictionaries into one. Specifically:
    1. If `overwrite` is True (used for manual.yaml), values in dict2 overwrite values in dict1 unconditionally.
    2. If `overwrite` is False, merge dictionaries while handling conflicts:
       a. If the values are the same, retain the value.
       b. If one value is None, use the non-null value.
       c. If both values differ and are non-null, combine them as "value 1 and value 2".

    Parameters:
        dict1:  The first dictionary
        dict2:  The second dictionary
        overwrite: Whether dict2 should take precedence unconditionally (used for manual.yaml).
    """
    # Handle the case where dict2 is None
    if dict2 is None:
        return dict1

    for key, value in dict2.items():
        if key in dict1:
            if isinstance(value, dict) and isinstance(dict1[key], dict):
                merge_dicts(dict1[key], value, overwrite=overwrite)
            elif overwrite:
                dict1[key] = value  # Overwrite unconditionally
            elif value and dict1[key] and value != dict1[key]:
                dict1[key] = f"{dict1[key]} and {value}"  # Combine values if there's a conflict
            elif not dict1[key]:
                dict1[key] = value  # Use non-null value if dict1[key] is None
        else:
            dict1[key] = value  # Add new key-value pairs from dict2

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
        # ("router_type", data["router_type"]),
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


if __name__ == "__main__":

    result_dir = "../result/"

    for manufacturer in os.listdir(result_dir):
        manufacturer_dir = os.path.join(result_dir, manufacturer)
        print("manufacturer: ", manufacturer)
        # For cisco, the result directory structure is different, so does the date file
        if manufacturer == "cisco":

            for series_dir in os.listdir(manufacturer_dir):
                series_folder = os.path.join(manufacturer_dir, series_dir)

                for root, dirs, files in os.walk(series_folder):
                    for router_dir in dirs:
                        merged_data = {"manufacturer": None, "series": None, "model": None, "slug": None, 
                                        "part_number": None, "u_height": None, "datasheet_url": None, "datasheet_pdf": None, 
                                        "release_date": None, "end_of_sale": None, "end_of_support": None,
                                        "max_throughput": None, "max_power_draw": None, "typical_power_draw": None, 
                                        "is_poe_capable": None, "max_poe_draw": None, "psu": None}
                                        # "router_type": None}
                        filtered_file_path = os.path.join(series_folder, router_dir, "filtered_netbox.yaml")
                        general_file_path = os.path.join(series_folder, router_dir, "general_llm.yaml")
                        date_file_path = os.path.join(series_folder, router_dir, "date_llm.yaml")
                        series_file_path = os.path.join(series_folder, router_dir, "series.yaml")

                        filtered_netbox_data = load_yaml(filtered_file_path) if os.path.isfile(filtered_file_path) else {}
                        general_data = load_yaml(general_file_path) if os.path.isfile(general_file_path) else {}
                        date_data = load_yaml(date_file_path) if os.path.isfile(date_file_path) else {}
                        series_data = load_yaml(series_file_path) if os.path.isfile(series_file_path) else {}
                        # type_data = load_yaml(os.path.join(series_folder, router_dir, "type_llm.yaml"))
                        
                        merge_dicts(merged_data, filtered_netbox_data)
                        merge_dicts(merged_data, general_data)
                        merge_dicts(merged_data, date_data)
                        merge_dicts(merged_data, series_data)
                        # merge_dicts(merged_data, type_data)

                        manual_file_path = os.path.join(series_folder, router_dir, "manual.yaml")
                        if os.path.isfile(manual_file_path):
                            manual_data = load_yaml(manual_file_path)
                            merge_dicts(merged_data, manual_data, overwrite=True)

                        organzed_data = organize_dicts(merged_data)
                        output_file = os.path.join(series_folder, router_dir, "merged.yaml")
                        save_yaml(organzed_data, output_file)


        else:
            for root, dirs, files in os.walk(manufacturer_dir):
                for router_dir in dirs:
                    merged_data = {"manufacturer": None, "series": None, "model": None, "slug": None, 
                                    "part_number": None, "u_height": None, "datasheet_url": None, "datasheet_pdf": None, 
                                    "release_date": None, "end_of_sale": None, "end_of_support": None,
                                    "max_throughput": None, "max_power_draw": None, "typical_power_draw": None, 
                                    "is_poe_capable": None, "max_poe_draw": None, "psu": None}
                                    # "router_type": None}
                    filtered_file_path = os.path.join(manufacturer_dir, router_dir, "filtered_netbox.yaml")
                    general_file_path = os.path.join(manufacturer_dir, router_dir, "general_llm.yaml")
                    manual_file_path = os.path.join(manufacturer_dir, router_dir, "manual.yaml")

                    filtered_netbox_data = load_yaml(filtered_file_path) if os.path.isfile(filtered_file_path) else {}
                    general_data = load_yaml(general_file_path) if os.path.isfile(general_file_path) else {}
                    # type_data = load_yaml(os.path.join(manufacturer_dir, router_dir, "type_llm.yaml"))
                    
                    merge_dicts(merged_data, filtered_netbox_data)
                    merge_dicts(merged_data, general_data)
                    # merge_dicts(merged_data, type_data)

                    if os.path.isfile(manual_file_path):
                        manual_data = load_yaml(manual_file_path)
                        merge_dicts(merged_data, manual_data, overwrite=True)

                    organzed_data = organize_dicts(merged_data)
                    output_file = os.path.join(manufacturer_dir, router_dir, "merged.yaml")
                    save_yaml(organzed_data, output_file)
