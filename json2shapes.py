import json
import re
import argparse
import configparser
import pandas


config = configparser.ConfigParser()
config.optionxform = str


def apply_aliases(name):

    if config['ALIASES']:
        new_name = name
        for k, v in config['ALIASES'].items():
            new_name = new_name.replace(k, v)
        return new_name
    else:
        return name


def convert(name):
    aliased_name = apply_aliases(name)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', aliased_name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()


def get_json_path(id_str):
    json_path = id_str.replace("/items/properties/", "[*].")
    json_path = json_path.replace("/properties/", ".")
    json_path = "$"+json_path
    return json_path


def ontology_sheet():

    columns = ['Ontology Name', 'Comment', 'Namespace URI', 'Prefix']
    data = []
    for ontology in [x for x in config if "Ontology" in x]:
        data.append({
            'Ontology Name': config[ontology]["name"],
            'Comment': config[ontology]["description"],
            'Namespace URI': config[ontology]["uri"],
            'Prefix': ontology[9:]
        })
    df = pandas.DataFrame().from_dict(data)
    return columns, df


def shapes_sheet(data):
    columns = ['Shape Id', 'Comment', 'Scope Class', 'Datasource', 'Shape Type', 'One Of', 'IRI Template']

    shapes = []
    shape_set = set()

    for row in data:
        shape = row["Shape Id"]
        if shape not in shape_set:
            shape_set.add(shape)
            datasource = "AwsAurora(AwsTableName:\"{}\")".format(shape.replace("shape:", ""))
            shapes.append({'Shape Id': shape, "Datasource": datasource})

    df = pandas.DataFrame().from_dict(shapes)
    return columns, df


def process(df, name, node, primary_key=None, ref_node=None, parent_node=None, prefix=None):

    if "properties" in node:

        properties = node["properties"]

        name_components = name.split("___")
        name2 = name if len(name_components) <= 2 else "___".join(name_components[-2:])
        name_uri = "shape:{}_{}".format(convert(prefix), convert(name2)) if prefix else "shape:{}".format(convert(name2))

        # synthetic key
        if not parent_node:
            df.append({'Shape Id': name_uri,
                       'Property Id': 'alias:STAGE_ID',
                       'Value Type': 'xsd:string',
                       'Stereotype': 'konig:syntheticKey',
                       'Min Count': 1,
                       'Max Count': 1,
                       'Max Length': 150
                       })

        if ref_node:

            fk_uri = "alias:{}_FK".format(convert(ref_node)) if "___" not in ref_node else "alias:{}__FK".format(convert(ref_node[ref_node.rfind("___")+3:]))

            df.append({'Shape Id': name_uri,
                       'Property Id': fk_uri,
                       'Value Type': 'xsd:string',
                       'Stereotype': 'konig:foreignKey',
                       'Min Count': 1,
                       'Max Count': 1,
                       'Max Length': 150
                       })

        for k, v in properties.items():

            if "type" in v and (v["type"] == "object" or "object" in v["type"]):
                prop = "{}___{}".format(parent_node, convert(k)) if parent_node else "{}".format(convert(k))
                process(df, name, v, parent_node=prop, prefix=prefix)

            elif "type" in v and (v["type"] == "array" or "array" in v["type"]):
                child_name = "{}___{}".format(name, k)
                process(df, child_name, v["items"], ref_node=name, prefix=prefix)

            else:
                prop = "alias:{}___{}".format(parent_node, convert(k)) if parent_node else "alias:{}".format(convert(k))
                row = {'Shape Id': name_uri, 'Property Id': prop, 'Remarks': get_json_path(v["$id"])}

                # determine 'Value Type'
                if "type" in v and (v["type"] == "string" or "string" in v["type"]):

                    # TODO we should add a format for integer vs decimal
                    if "format" in v and (v["format"] == "number" or "number" in v["format"]):
                        row.update({'Value Type': "xsd:decimal"})
                    elif "format" in v and (v["format"] == "date-time" or "date-time" in v["format"]):
                        row.update({'Value Type': "xsd:dateTime"})
                    else:
                        row.update({'Value Type': 'xsd:string'})
                else:
                    row.update({'Value Type': 'xsd:string'})

                if "maxLength" in v and v["maxLength"] and v["maxLength"] != "N/A":
                    row.update({'Max Length': int(v["maxLength"])})
                elif "type" in v and (v["type"] == "string" or "string" in v["type"]):
                    row.update({'Max Length': 150})

                if "type" in v and "null" in v["type"]:
                    row.update({'Min Count': 0})
                else:
                    row.update({'Min Count': 1})

                row.update({'Max Count': 1})

                if k == primary_key:
                    row.update({'Stereotype': 'konig:primaryKey', 'Min Count': 1})

                df.append(row)


def run(args):

    df = []

    if args.config:
        config.read(args.config)

    prefix = config["GENERAL"].get("prefix", None)
    base = config["GENERAL"].get("base", None)
    primary_key = config["PRIMARY KEYS"].get(base, None)

    with open(args.schema) as json_schema:
        schema = json.load(json_schema)
        process(df, base, schema, primary_key=primary_key, prefix=prefix)

    writer = pandas.ExcelWriter(args.workbook)

    ontology_columns, ontology_df = ontology_sheet()
    ontology_df.to_excel(writer, 'Ontologies', columns=ontology_columns, index=False)

    shapes_columns, shapes_df = shapes_sheet(df)
    shapes_df.to_excel(writer, 'Shapes', columns=shapes_columns, index=False)

    columns = ['Shape Id', 'Property Id', 'Remarks', 'Value Type', 'Stereotype', 'Min Count', 'Max Count', 'Max Length']
    _df = pandas.DataFrame().from_dict(df)
    _df.to_excel(writer, 'Property Constraints', columns=columns, index=False)

    writer.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to INI config file')
    parser.add_argument('schema', help='base JSON schema')
    parser.add_argument('workbook', help='workbook with data shapes')
    args = parser.parse_args()
    run(args)
