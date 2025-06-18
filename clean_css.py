import os
import re

def extract_selectors_from_css(css_content):
    # Match .class or #id selectors only (avoid tag selectors or pseudo classes)
    class_pattern = re.compile(r'\.([a-zA-Z0-9_-]+)')
    id_pattern = re.compile(r'#([a-zA-Z0-9_-]+)')

    classes = set(class_pattern.findall(css_content))
    ids = set(id_pattern.findall(css_content))

    return classes, ids

def extract_used_classes_and_ids_from_html(html_content):
    class_pattern = re.compile(r'class\s*=\s*["\']([^"\']+)["\']')
    id_pattern = re.compile(r'id\s*=\s*["\']([^"\']+)["\']')

    used_classes = set()
    used_ids = set()

    for match in class_pattern.findall(html_content):
        used_classes.update(match.split())  # multiple classes in one attribute

    used_ids.update(id_pattern.findall(html_content))

    return used_classes, used_ids

def find_unused_css_selectors(html_dir, css_dir):
    all_used_classes = set()
    all_used_ids = set()

    # 1. Read and parse all HTML files
    for root, _, files in os.walk(html_dir):
        for file in files:
            if file.endswith('.html'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    html = f.read()
                    used_classes, used_ids = extract_used_classes_and_ids_from_html(html)
                    all_used_classes.update(used_classes)
                    all_used_ids.update(used_ids)

    # 2. Read and parse all CSS files
    for root, _, files in os.walk(css_dir):
        for file in files:
            if file.endswith('.css'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    css = f.read()
                    css_classes, css_ids = extract_selectors_from_css(css)

                    # 3. Check for unused classes
                    unused_classes = css_classes - all_used_classes
                    unused_ids = css_ids - all_used_ids

                    if unused_classes or unused_ids:
                        print(f"
In {file}:")
                        for cls in sorted(unused_classes):
                            print(f"  Unused class: .{cls}")
                        for id_ in sorted(unused_ids):
                            print(f"  Unused id: #{id_}")

if __name__ == "__main__":
    html_directory = '/home/juan/dev/python-dev/search_engine/templates'
    css_directory =  '/home/juan/dev/python-dev/search_engine/static/css'
    find_unused_css_selectors(html_directory, css_directory)
