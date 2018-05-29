import json
import re
import argparse
import configparser
import pandas


config = configparser.ConfigParser()
config.optionxform = str
UNSIGNED_INT_MAX = 4294967295


def apply_aliases(name):

    if config['ALIASES']:
        new_name = name
        for k, v in config['ALIASES'].items():
            new_name = re.sub(k, v, new_name)
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


def settings_sheet():
    columns = ['Setting Name', 'Setting Value', 'Pattern', 'Replacement']
    data = []
    for setting in [x for x in config if "Setting" in x]:
        data.append({
            'Setting Name': setting[8:],
            'Setting Value': config[setting]["value"],
            'Pattern': config[setting]["pattern"] if "pattern" in config[setting] else None,
            'Replacement': config[setting]["replacement"] if "replacement" in config[setting] else None
        })
    df = pandas.DataFrame().from_dict(data)
    return columns, df


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


def determine_datatype(property):

    if "type" in property:

        if property["type"] == "integer" or "integer" in property["type"]:
            return "xsd:integer"

        elif property["type"] == "number" or "number" in property["type"]:
            return "xsd:decimal"

        elif property["type"] == "string" or "string" in property["type"]:
            if "format" in property:
                if property["format"] == "number" or "number" in property["format"]:
                    return "xsd:decimal"

                elif property["format"] == "integer" or "integer" in property["format"]:
                    return "xsd:integer"

                elif property["format"] == "date-time" or "date-time" in property["format"]:
                    return "xsd:dateTime"
                else:
                    return "xsd:string"
            else:
                return "xsd:string"

    else:
        return "xsd:string"

    if "type" in property and (property["type"] == "string" or "string" in property["type"]):

        if "format" in property:

            if property["format"] == "number" or "number" in property["format"]:
                return "xsd:decimal"

            elif property["format"] == "integer" or "integer" in property["format"]:
                return "xsd:integer"

            elif property["format"] == "date-time" or "date-time" in property["format"]:
                return "xsd:dateTime"
            else:
                return "xsd:string"

        else:
            return "xsd:string"
    else:
        return "xsd:string"


def determine_min_count(property):
    if "type" in property and "null" in property["type"]:
        return 0
    else:
        return 1


def determine_min_inclusive(property):

    datatype = determine_datatype(property)

    if datatype == "xsd:integer":
        if "minimum" in property:
            return property["minimum"]
        else:
            return 0
    else:
        return None


def determine_max_exclusive(property):

    datatype = determine_datatype(property)

    if datatype == "xsd:integer":
        if "maximum" in property:
            return property["maximum"]
        else:
            return UNSIGNED_INT_MAX
    else:
        return None


def determine_max_length(property, default=1000):
    datatype = determine_datatype(property)
    if datatype == "xsd:string":
        if "maxLength" in property and property["maxLength"] != "N/A":
            return int(property["maxLength"])
        else:
            return default
    else:
        return None


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


def embed_object(property):
    if len(property["properties"]) > 10:
        return False
    else:
        return True


def add_synthetic_keys(node):

    if "properties" in node:
        properties = node["properties"]
        found_id = False
        for k, v in properties.items():
            if k == "id":
                found_id = True

            if "type" in v and (v["type"] == "object" or "object" in v["type"]):
                if not embed_object(v):
                    add_synthetic_keys(v)

        if not found_id:
            properties.update({"stageId": {
                "$id": node["$id"]+"/properties/stageId",
                "type": "integer",
                "minimum": 0,
                "maximum": UNSIGNED_INT_MAX,
                "exclusiveMaximum": True}
            })


def process(df, name, node, primary_key=None, ref_node=None, parent_node=None, parent_id=None, prefix=None):

    if "properties" in node:

        properties = node["properties"]

        name_components = [convert(x) for x in name.split("__")]
        name2 = name if len(name_components) <= 2 else "__".join(name_components[-2:])
        name_uri = "shape:{}_{}".format(convert(prefix), convert(name2)) if prefix else "shape:{}".format(convert(name2))

        if ref_node and parent_id:

            fk_uri = "alias:{}_FK".format(convert(ref_node))

            # add foreign key and array index (for preserving order)

            df.append({'Shape Id': name_uri,
                       'Property Id': fk_uri,
                       'Value Type': parent_id["datatype"],
                       'Min Inclusive': parent_id["minInclusive"],
                       "Max Exclusive": parent_id["maxExclusive"],
                       'Stereotype': 'konig:foreignKey',
                       'Remarks': 'references {}_{}.{}'.format(prefix, convert(ref_node), parent_id["Field"]),
                       'Min Count': 1,
                       'Max Count': 1,
                       'Max Length': parent_id["maxLength"]
                       })

            df.append({'Shape Id': name_uri,
                       'Property Id': "alias:STAGE_INDEX",
                       'Value Type': 'xsd:integer',
                       'Min Inclusive': 0,
                       'Max Exclusive': 4294967295,
                       'Stereotype': None,
                       'Remarks': None,
                       'Min Count': 1,
                       'Max Count': 1,
                       'Max Length': None
                      })

        primary_key_prop = { }

        for k, v in properties.items():

            # NOTE - this only works if the id comes before any nested objects
            # TODO replace with an implementation of JSON PATH queries
            if k == "id" or k == "stageId":
                primary_key_prop["Field"] = convert(k)
                primary_key_prop["datatype"] = determine_datatype(v)
                primary_key_prop["minInclusive"] = determine_min_inclusive(v)
                primary_key_prop["maxExclusive"] = determine_max_exclusive(v)
                primary_key_prop["maxLength"] = determine_max_length(v)

            if "type" in v and (v["type"] == "object" or "object" in v["type"]):

                if len(v["properties"]) <= 10:
                    prop = "{}__{}".format(parent_node, convert(k)) if parent_node else "{}".format(convert(k))
                    process(df, name, v, parent_node=prop, prefix=prefix)
                else:
                    child_name = "{}__{}".format(name, k)
                    process(df, child_name, v, ref_node=name, parent_id=primary_key_prop, prefix=prefix)

            elif "type" in v and (v["type"] == "array" or "array" in v["type"]):
                child_name = "{}__{}".format(name, k)
                process(df, child_name, v["items"], ref_node=name, prefix=prefix)

            else:
                prop = "alias:{}__{}".format(parent_node, convert(k)) if parent_node else "alias:{}".format(convert(k))
                row = {'Shape Id': name_uri, 'Property Id': prop}

                if k != "stageId":
                    row.update({'Remarks': get_json_path(v["$id"])})

                row.update({'Value Type': determine_datatype(v)})
                row.update({'Max Length': determine_max_length(v)})
                row.update({'Min Count': determine_min_count(v)})
                row.update({'Max Count': 1})

                if k == "stageId":
                    row.update({'Stereotype': "konig:syntheticKey", "Min Count": 1})

                if k == primary_key:
                    row.update({'Stereotype': 'konig:primaryKey', 'Min Count': 1})
                elif k == "id":
                    row.update({'Stereotype': "konig:primaryKey", "Min Count": 1})

                if "description" in v:
                    row.update({'Comment': v['description']})

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
        add_synthetic_keys(schema)
        process(df, base, schema, primary_key=primary_key, prefix=prefix)

    writer = pandas.ExcelWriter(args.workbook)

    ontology_columns, ontology_df = ontology_sheet()
    ontology_df.to_excel(writer, 'Ontologies', columns=ontology_columns, index=False)

    shapes_columns, shapes_df = shapes_sheet(df)
    shapes_df.to_excel(writer, 'Shapes', columns=shapes_columns, index=False)

    columns = ['Shape Id', 'Property Id', 'Comment', 'Remarks', 'Value Type', 'Stereotype', 'Min Count', 'Max Count', 'Max Length', 'Min Inclusive', 'Max Exclusive', 'Decimal Precision', 'Decimal Scale']
    _df = pandas.DataFrame().from_dict(df)
    _df.to_excel(writer, 'Property Constraints', columns=columns, index=False)

    settings_columns, settings_df = settings_sheet()
    settings_df.to_excel(writer, 'Settings', columns=settings_columns, index=False)

    writer.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to INI config file')
    parser.add_argument('schema', help='base JSON schema')
    parser.add_argument('workbook', help='workbook with data shapes')
    args = parser.parse_args()
    run(args)
