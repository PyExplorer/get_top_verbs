import ast
import collections
import json
from argparse import ArgumentParser
from os import path as os_path
from os import walk as os_walk

# this part needs only once
from nltk import download
from nltk import pos_tag

download('averaged_perceptron_tagger')

CONFIG = {
    'projects': [
        'django',
        'flask',
        'pyramid',
        'reddit',
        'requests',
        'sqlalchemy',
    ]
}


def parse_args():
    parser = ArgumentParser(description='Static verb code analyser.')
    parser.add_argument('-p', '--path', type=str, default='.', dest='path')
    parser.add_argument('-d', '--dirs', type=str, dest='dirs')

    parser.add_argument("-c", "--config",
                        default="config.json",
                        help="Set the path for config.json",
                        dest='config_path')
    return parser.parse_args()


def merge_two_config(a, b):
    c = a.copy()
    c.update(b)
    return c


def get_config_from_file(config_file):
    try:
        with open(config_file) as json_data_file:
            config_from_file = json.load(json_data_file)
        return config_from_file
    except ValueError:
        print("File " + config_file + " is corrupted and can't be parsed")
        return {}


def flat(_list):
    """ [(1,2), (3,4)] -> [1, 2, 3, 4]"""
    res = []
    for item in _list:
        res.extend(list(item))
    return res


def check_is_verb_with_ntlk(word):
    if not word:
        return False
    pos_info = pos_tag([word])
    return pos_info[0][1] == 'VB'


def is_function_name_valid(func):
    return not (func.startswith('__') and func.endswith('__'))


def get_filenames_with_ext_in_path(path, ext='.py', max_size=100):
    filenames = []
    for dirname, dirs, files in os_walk(path, topdown=True):
        for file in files:
            if not file.endswith(ext):
                continue
            filenames.append(os_path.join(dirname, file))
            if len(filenames) == max_size:
                break

    print('total {} files'.format(len(filenames)))
    return filenames


def get_trees(path, with_filenames=False, with_file_content=False):
    filenames = get_filenames_with_ext_in_path(path)

    trees = []
    for filename in filenames:
        with open(filename, 'r', encoding='utf-8') as opened_file:
            main_file_content = opened_file.read()
        try:
            tree = ast.parse(main_file_content)
        except SyntaxError as e:
            print(e)
            tree = None
        except Exception as e:
            print('Something went wrong %s' % (e,))
            tree = None

        if not tree:
            continue

        if not with_filenames:
            trees.append(tree)
            continue

        if with_file_content:
            trees.append((filename, main_file_content, tree))
            continue

        trees.append((filename, tree))

    print('{} trees generated'.format(len(trees)))
    return trees


def get_verbs_from_function_name(function_name):
    verbs = []
    for word in function_name.split('_'):
        if not check_is_verb_with_ntlk(word):
            continue
        verbs.append(word)
    return verbs


def get_functions_from_trees(trees):
    functions = []
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            functions.append(node.name.lower())
    return functions


def get_valid_functions_names_from_functions(functions):
    functions_names = []
    for func in functions:
        if is_function_name_valid(func):
            functions_names.append(func)
    return functions_names


def get_most_common_words(words, top_size=200):
    return collections.Counter(words).most_common(top_size)


def get_top_verbs_in_path(path, top_size=10):
    print('--- {} ---'.format(path))
    trees = get_trees(path)
    functions = get_functions_from_trees(trees)
    functions_names = get_valid_functions_names_from_functions(functions)
    print('{} functions extracted'.format(len(functions_names)))
    verbs = []
    for function_name in functions_names:
        verbs_from_function = get_verbs_from_function_name(function_name)
        verbs.extend(verbs_from_function)
    verbs = get_most_common_words(verbs, top_size)
    print('{} verbs extracted'.format(len(verbs)))

    return verbs


def get_top_verbs_from_dirs(dirs):
    verbs = []
    for one_dir in dirs:
        path = os_path.join('.', one_dir)
        verbs.extend(get_top_verbs_in_path(path))
    return verbs


def print_results(results):
    for result in results:
        print(*result)


def main():
    args = parse_args()

    config_from_file = get_config_from_file(args.config_path)

    merged_config = merge_two_config(CONFIG, config_from_file)

    if not args.dirs:
        top_verbs = get_top_verbs_in_path(args.path)
    else:
        top_verbs = get_top_verbs_from_dirs(merged_config.get('dirs'))

    print('total {} words, {} unique'.format(
        len(top_verbs), len(set(top_verbs)))
    )

    most_common_words = get_most_common_words(top_verbs)

    print_results(most_common_words)


if __name__ == '__main__':
    main()
