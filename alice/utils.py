import re


def cp_models(old_model_file, new_model_file, new_app):
    """
    cp models file to old_models.py and rename model app
    :param old_app:
    :param new_app:
    :param old_model_file:
    :param new_model_file:
    :return:r
    """
    pattern = r'(ManyToManyField|ForeignKeyField|OneToOneField)\((model_name)?(\"|\')(?P<app>\w+).+\)'
    with open(old_model_file, 'r') as f:
        content = f.read()
    ret = re.sub(pattern, rf'{new_app} \g<app>', content)
    print(ret)
