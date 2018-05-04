import csv
import json
import argparse


def load_attr_mappings(mappingsfile):
    attr_mappings = []
    with open(mappingsfile, 'r') as attr_mapping_csv:
        next(attr_mapping_csv) # skip first line
        reader = csv.DictReader(attr_mapping_csv)
        for row in reader:
            attr_mappings.append(row)
    return attr_mappings


def load_vocabs(lovfile):

    vocabs = {}

    with open(lovfile, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            value_set = row['Value Set Name']
            item = row['Value']

            if value_set not in vocabs:
                vocabs.update({value_set: [item]})
            else:
                vocabs[value_set].append(item)

    for k, v in vocabs.items():
        vocabs[k].append(None)

    return vocabs


def process_properties(properties, attr_mappings):

    for k, v in properties.items():
        if "type" in v and "object" not in v["type"] and "array" not in v["type"]:

            # print("looking for attribute mapping for", k)
            attr_mapping = next((x for x in attr_mappings if x['Semantic Json Name'] == k), None)
            if attr_mapping:

                if attr_mapping['Attribute Data Type'] == "Character":
                    # v.update({'type': 'string'})
                    # v.update({'maxLength': attr_mapping['Length']})
                    pass

                if attr_mapping['Attribute Data Type'] == "Number":
                    v.update({'format': 'number'})

                if attr_mapping['Attribute Data Type'] == "Date":
                    v.update({'format': 'date-time'})

                if attr_mapping["Length"].strip() != "N/A":
                    v.update({'maxLength': attr_mapping['Length']})

        elif "type" in v and "object" in v["type"]:
            process_properties(v["properties"], attr_mappings)
        elif "type" in v and "array" in v["type"]:
            item = v["items"]
            if "properties" in item:
                process_properties(item["properties"], attr_mappings)


def run(args):

    # load MDM Attribute mappings
    attr_mappings = load_attr_mappings(args.mapping)

    # load MDM List of Values (LOVs)
    # vocabs = load_vocabs(args.lov)

    # load base JSON schema
    with open(args.infile) as json_data:
        schema = json.load(json_data)
        # schema["definitions"].update(vocabs)

        properties = schema["properties"]
        process_properties(properties, attr_mappings)

    with open(args.outfile, 'w') as outfile:
        json.dump(schema, outfile, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--mapping', help="MDM Attribute Mapping CSV", default='MDM_Generic_Outbound_Attributes_V1.9.xlsx - Attribute Mapping.csv')
    parser.add_argument('--lov', help="MDM LOV CSV", default="MDM_Generic_Outbound_Attributes_V1.9.xlsx - LOV's.csv")
    parser.add_argument('infile', help='base JSON schema')
    parser.add_argument('outfile', help='enriched JSON schema')

    args = parser.parse_args()
    run(args)
