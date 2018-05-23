import json
import re
import argparse
import configparser
from pprint import pprint

config = configparser.ConfigParser()
config.optionxform = str

classes = {}


def pascal_case(name):
    return "%s%s" % (name[0].upper(), name[1:])


def get_datatype(datatype):
    if datatype == "date-time":
        return "DateTime"
    elif datatype == "number":
        return "Number"
    else:
        return datatype


def print_uml():
    print("@startuml")

    for k, v in classes.items():
        print("class {} {{".format(k))
        for attribute in classes[k]["attributes"]:
            print("\t{} : {}".format(attribute["name"], get_datatype(attribute["datatype"])))

        print("}")

        for child in classes[k]["children"]:
            print("{} --> \"0..1\" {} : {}".format(k, pascal_case(child["name"]), child["name"]))

        for array in classes[k]["arrays"]:
            print("{} --> \"0..*\" {} : {}".format(k, pascal_case(array["name"]), array["name"]))

        print("")

    print("@enduml")


def process(node, name):

    if "type" in node and "object" in node["type"] and "properties" in node:

        class_name = pascal_case(name)

        classes.update({class_name: {"attributes": [], "arrays": [], "children": []}})

        properties = node["properties"]
        for k, v in properties.items():

            if "type" in v and (v["type"] == "object" or "object" in v["type"]):
                classes[class_name]["children"].append({"name": k})
                process(v, k)

            elif "type" in v and (v["type"] == "array" or "array" in v["type"]):
                classes[class_name]["arrays"].append({"name": k})
                process(v["items"], k)

            else:
                max_length = v["maxLength"] if "maxLength" in v else None
                datatype = v["format"] if "format" in v else "String"
                classes[class_name]["attributes"].append({"name": k, "maxLength": max_length, "datatype": datatype})


def run(args):

    with open(args.schema) as json_schema:
        schema = json.load(json_schema)
        process(schema, "Product")

    print_uml()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument('--config', help='path to INI config file')
    parser.add_argument('schema', help='JSON schema')
    # parser.add_argument('output', help='PlantUML spec')
    args = parser.parse_args()
    run(args)