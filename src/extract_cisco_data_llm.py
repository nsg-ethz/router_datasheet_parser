"""
Parameters we care about:
1. name
2. vendor
3. datasheet url
4. datasheet file
5. typical power (w)
6. typical power (desc)
7. max power (w)
8. max poewr (desc)
9. max throughput (tbps)
10. release (pending)
11. end-of-sale (pending)
12. end-of-support (pending)
13. numbers of psus
14. psu power (w)
15. psu rating
"""

import json
import random
import os
import re
from typing import Literal, Optional

import pandas as pd
import requests
import tiktoken
from markdownify import markdownify as md
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm

# Set random seed
random.seed(40)

class Power(BaseModel):
    value: int = Field(description="The value in watts")
    power_description: Optional[str] = Field(description="The power description that may be associated with the power value (such as the temperature, throughput, ...)")

class RouterData(BaseModel):
    name: str = Field(description="The name of the router model")
    vendor: str = Field(description="The vendor of this router, e.g., Cisco, Citrix, etc.")
    datasheet_file: str = Field(description="The pdf file stroing the information on this router device")
    typical_power: Optional[Power] = Field(description="The typical power consumption of the router")
    max_power: Optional[Power] = Field(description="The maximum power consumption of the router")
    max_throughput: float = Field(description="The maximum throughput or the bandwidth used in the url, typically in the unit of Tbps")
    release_date: Optional[str] = Field(description="Day the router series was released (YYYY-MM-DD format)")
    end_of_sale: Optional[str] = Field(description="The last day which this router was sold (YYYY-MM-DD format)")
    end_of_support: Optional[str] = Field(description="The last day this router was officially supported (YYYY-MM-DD format)")
    num_psu: int = Field(description="The number of Power Supply Units (PSUs)")
    psu_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="If provided, the rating of the router's Power Supply Unit (PSU)")

PERSONA         =   "You are a knowledgeable network engineer with expertise in router technologies."
HIGH_LEVEL_TASK =   "You are tasked with gathering detailed information on various routers within your network." \
                    "Your objective is to scan provided URLs that contain router data and extract relevant information about the PSUs." 
LOW_LEVEL_TASK  =   lambda name: f"I will give you the URL containing the information you are after. You are looking for the data relevant only to router {name}" \
                    "Your task is to use your expertise and the URL I provided to try to extract the information and fill out the fields of the given structure. " \
                    "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
                    "Only use the information contained in the URL." \
                    "Please pay attention to that the URL is the router series, meaning that it will contain the info of other routers in the same series.\n" \
                    "For example, on the url of router 8201-32FH, it will contain information of Cisco 8201-SYS.\n" \
                    "Your goal is to avoid grapping info of Cisco 8201-SYS and pay attention to only 8202-32FH."

# For future reference, can build Lambdas into this using: TEXT_AMOUNT = lambda amount: f'text {amount}'
system_prompt = lambda name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(name)])

if __name__ == "__main__":
    client = OpenAI()
    # Create a data structure to hold the information
    data = {}

    """
    There are 689 files in total under Cisco.
    268 of them contain the URL.
    Let's take 8201-31FH as an exmaple, and then extend to others later on.
    """
    file = "../dataset/Cisco/8201-32FH.yaml"
    vendor, name = file.split('/')[-2].split('.')[0].lower(), file.split('/')[-1].split('.')[0]
    url_pattern = re.compile(r'https:\/\/[^\/]+\/[^ ]+\.html')
    with open(file, 'r') as f:
        content = f.read()
        url = url_pattern.search(content).group()
    print(f"url: {url}")
    html_content = requests.get(url).text

    """
    I actually don't really get it why it shall be transferred to the md file.
    But let's just do it currently.
    """
    markdown_content = md(html_content)
    os.makedirs("../result/markdown", exist_ok=True)
    with open(f"../result/markdown/{name}.md", "w") as f:
        f.write(markdown_content)
    
    # Call the OpenAI API
    try:
        completion = client.beta.chat.completions.parse(
            temperature=0,
            model="gpt-4o-2024-08-06", #"gpt-4o-mini", #"gpt-4o-2024-08-06", 
            messages=[ 
                {
                    "role": "system", 
                    "content": system_prompt(name)
                },
                {
                    "role": "user",
                    "content": markdown_content
                }
            ],
            response_format=RouterData,
        )

        # Get the output from your API call
        output = completion.choices[0].message.parsed
        print(f"output: {output}")
        # Dump the model to a dictionary with JSON-compatible formatting
        output_dict = output.model_dump(mode='json')
        if not output_dict["datasheet_file"].startswith('https:'):
            output_dict["datasheet_file"] = "https://www." + str(vendor) + ".com" + output_dict["datasheet_file"]
        print(f"output_dict: {output_dict}")
        # Print the dictionary with indentation using json.dumps()
        output = json.dumps(output_dict, indent=4)
        #print(output)
        data[name] = output_dict
    except Exception as e:
        print(f"Error: {e}")
        pass
    
    # Save the data to a file
    with open("../result/data.json", "w") as f:
        json.dump(data, f, indent=4)
    

