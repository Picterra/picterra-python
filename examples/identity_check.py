from picterra import APIClient

org_name = APIClient().who_am_i()["organization_name"]
name = input(f"Are you ok using {org_name}? (Y/N)")
if name.lower()[0] != 'y':
    exit()
# rest of the code
