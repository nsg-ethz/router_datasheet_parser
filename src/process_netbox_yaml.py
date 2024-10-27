import csv
import json
import re
import os
import yaml
from tqdm import tqdm


def write_netbox_result(psu_category, router_dir):
    """
    Write all the necessary information which can be extracted from the original
    netbox yaml file. Specifically speaking, they are:
        -   manufacturer
        -   model
        -   slug
        -   part_number
        -   u_height
        -   url (if it exists, otherwise log it in routers_without_url.csv)
        -   PSU:
            -   number_of_modules
            -   power_rating (maximum_draw)
            -   part_numbe (type)
    
    Parameters:
        psu_category:   a json file which was created in count_netbox_keys
                        to judge if a power-ports or module-bays is a PSU
                        module or not.
        router_dir:     A router dictory storing all the netbox router info
    
    Returns:
        yaml:           A yaml file with the name format 
                        <router_model>_filtered_netbox.yaml
                        containing the information mentioned above.
    """
    # Load .json for the PSU category
    with open(psu_category, "r") as json_file:
        data = json.load(json_file)
        psu_list = data["psu"]
        non_psu_list = data["non_psu"]
    
    with open("../result/routers_without_url.csv", mode="w", newline="") as routers_without_url:
        writer = csv.writer(routers_without_url)
        writer.writerow(["manufacturer", "model"])

    files = [f for f in os.listdir(router_dir) if os.path.isfile(os.path.join(router_dir, f))]
    # testing files
    # files = ["2951-ISR.yaml", "8201-24H8FH.yaml", "ASR1002-HX.yaml"] 
    for filename in tqdm(files):
        with open(os.path.join(router_dir, filename), "r") as f:
            content = yaml.safe_load(f)

        # Create a folder for a specific router
        output_dir = "../result/" + str(content["manufacturer"]) + "/" + str(content["model"]) + "/"
        filter_netbox_yaml_file = str(content["model"]) + "_filtered_netbox.yaml"
        os.makedirs(output_dir, exist_ok=True)

        # Get prepared for writing this router info
        output_dict = {}
        output_dict["manufacturer"] = content.get("manufacturer", output_dict.get("manufacturer"))
        output_dict["model"] = content.get("model", output_dict.get("model"))
        print("model: ", output_dict["model"])
        output_dict["slug"] = content.get("slug", output_dict.get("slug"))
        output_dict["part_number"] = content.get("part_number", output_dict.get("part_number"))
        output_dict["u_height"] = content.get("u_height", output_dict.get("u_height"))

        # Log the model name in the CSV if "url is missing"
        url = content.get("comments")
        url_pattern = re.compile(r'https?://[^\s]+')
        url_match = url_pattern.search(str(url))
        if url_match:
            url = url_match.group()[:-1]
            output_dict["url"] = url
        else:
            with open("../result/routers_without_url.csv", mode="a", newline="") as routers_without_url:
                writer = csv.writer(routers_without_url)
                writer.writerow([output_dict["manufacturer"], output_dict["model"]])

        """
        PSU related:
        1. efficiency_rating -> [Bronze, Silver, Gold, Platinum, Titanium] -> LLM
        2. power_rating -> maximum_draw -> netbox
        3. numbers_of_modules -> netbox
        4. part_number -> netbox
        """
        output_dict["PSU"] = {"number_of_modules": 0, "efficiency_rating": None, "power_rating": None, "part_number": None}

        # Iterate over potential power sources if they exist
        for key in ["power-ports", "module-bays"]:
            if content.get(key):
                for module in content[key]:
                    if module["name"] in psu_list:
                        print("module: ", module)
                        output_dict["PSU"]["number_of_modules"] += 1
                        output_dict["PSU"]["power_rating"] = module.get("maximum_draw", None)
                        output_dict["PSU"]["part_number"] = module.get("type", None)
                # Exit after processing "power-ports" if found
                break
        
        # Write the output_dict to the yaml
        with open(output_dir+filter_netbox_yaml_file, "w") as yaml_file:
            yaml.dump(output_dict, yaml_file, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":

    router_dir = "../dataset/Cisco/"

    psu_category = "psu_category.json"
    write_netbox_result(psu_category, router_dir)
