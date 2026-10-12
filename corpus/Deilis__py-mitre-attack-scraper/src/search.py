import json
import os
import argparse
from utils import load_groups_data, display_group_info, cache_group_data


def search_group_by_name_or_id(groups_data, query):
   
    """Search for a group by name or ID."""
   
    query = query.strip().lower()
    for group in groups_data:
        if query in group['ID'].lower() or query in group['Name'].lower():
            return group
    return None


def search_groups_by_associate(groups_data, associate):
   
    """Search for all groups mentioning a specific associate."""
   
    associate = associate.strip().lower()
    associated_groups = []
    for group in groups_data:
        if associate in group['Associated Groups'].lower():
            associated_groups.append(group)
    return associated_groups


def main():

    #ARGs parser
    parser = argparse.ArgumentParser(description='Search MITRE ATT&CK group information.')
    parser.add_argument('--name', type=str, help='Search group information by name')
    parser.add_argument('--id', type=str, help='Search group information by ID')
    parser.add_argument('--associate', type=str, help='Search groups mentioning an associate')
    parser.add_argument('--input', type=str, default='data/groups_info/data.json', help='Input file path to read the group data')

    #Parse ARGs
    args = parser.parse_args()

    #Loads DATA
    groups_data = load_groups_data(args.input)

    #Performs search
    if args.name:
        group = search_group_by_name_or_id(groups_data, args.name)
        display_group_info(group)
        if group:
            cache_group_data(group, f"data/groups/{group['ID']}")

    if args.id:
        group = search_group_by_name_or_id(groups_data, args.id)
        display_group_info(group)
        if group:
            cache_group_data(group, f"data/groups/{group['ID']}")

    if args.associate:
        associated_groups = search_groups_by_associate(groups_data, args.associate)
        if associated_groups:
            for group in associated_groups:
                display_group_info(group)
                cache_group_data(group, f"data/groups/{group['ID']}")
        else:
            print(f"No groups found mentioning {args.associate}")


if __name__ == '__main__':
    main()
