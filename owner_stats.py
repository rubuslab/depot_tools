from __future__ import print_function

import argparse
import collections
import os
import re
import subprocess

import owners

def get_all_files(search_root, tree_root):
    all_files = []

    # Could also use git ls-tree --full-tree -r --name-only HEAD
    for root, dirs, files in os.walk(search_root):
        if ".git" in dirs or ".svn" in dirs:
            if root != tree_root:
                # print("Ignoring external repo %s" % root)
                del dirs[:]
                continue

        # Don't recurse into dot dirs like .git or .svn or .pycache.
        dirs[:] = [d for d in dirs if not (d[0] == "." or
                                           "sysroot" in d)]
        # Ignore the android sdk public dir since it has a lot of
        # files that won't be individually maintained.
        if root.endswith("android_sdk") and "public" in dirs:
            del dirs[dirs.index("public")]

        for f in files + dirs:
            all_files.append(os.path.relpath(os.path.join(root, f),
                                             tree_root))

    return all_files

def get_active_reviewers(tree_root, since):
    reviewers = collections.Counter()
    one_year_log = subprocess.check_output(["git", "log",
                                            "--since", since],
                                           cwd=tree_root)

    for line in one_year_log.split("\n"):
        line = line.strip()
        if line.startswith("Reviewed-by: "):
            reviewer = line[line.index("<")+1:line.index(">")]
            if ("gserviceaccount" not in reviewer and
                "autoroll" not in reviewer and
                "chromium-" not in reviewer):
                reviewers[reviewer] += 1

    return reviewers

def get_files_with_owner_counts(owners_per_file, only_these_owners=None):
    owners_per_file_counter = collections.Counter()
    for filename, owner_set in owners_per_file.iteritems():
        if "*" in owner_set:
            owners_per_file_counter[filename] += 10000 # Like "infinity"
        else:
            if only_these_owners:
                owner_set = owner_set & only_these_owners
            owners_per_file_counter[filename] += len(owner_set)

    return owners_per_file_counter

def _get_active_owners_for_file(file_or_dir, owners_per_file, active_reviewers):
    return ", ".join(list(owners_per_file[file_or_dir] & active_reviewers))

def censor_email(text):
    """Make foo@chromium.org into foo@chr."""
    return re.sub(r"(@[a-z]{3})[a-z]*(\.[a-z]*)+", r"\1", text)

def mail_filtered_print(text, end="\n"):
    text = censor_email(str(text))
    print(text, end=end)

def header_print(header):
    print()
    print(header)
    print("-" * len(header))

def main():
    """Main code"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True,
                        help="Root of the source tree")
    parser.add_argument("--only-subtree",
                        help="If given, limit stats to this subtree")
    parser.add_argument("--inactive-since", default="14 months",
                        help="Grace period until considered inactive")
    args = parser.parse_args()

    print("Scanning tree for all possible files to own.")

    if args.only_subtree:
        all_files = get_all_files(args.only_subtree, args.root)
    else:
        all_files = get_all_files(args.root, args.root)

    print("Found %d files." % len(all_files))

    print("Reading OWNERS files")
    owners_db = owners.Database(args.root, open, os.path)
    owners_db.load_data_needed_for(all_files)

    print("Mapping owners to files (checking 30,000 files per second)")
    all_owners = owners_db.all_possible_owners(all_files, None)

    since = args.inactive_since
    print("Fetching the list of active (%s) reviewers" % since)
    active_reviewers = get_active_reviewers(args.root, since)
    # mail_filtered_print(active_reviewers.most_common(20))
    # mail_filtered_print(list(reversed(active_reviewers.most_common()))[:30])
    print("The tree has %d active (%s) reviewers" % (len(active_reviewers),
                                                     since))

    active_reviewers = set(active_reviewers.keys())

    files_per_owner_counter = collections.Counter()
    owners_per_file = {}

    for owner, file_dist_list in all_owners.iteritems():
        files_per_owner_counter[owner] += len(file_dist_list)
        for filename, _distance in file_dist_list:
            owner_set = owners_per_file.setdefault(filename, set())
            owner_set.add(owner)

    header_print("Owners with the most files:")
    for owner, count in files_per_owner_counter.most_common(10):
        if owner == "*":
            continue
        mail_filtered_print("%s\t%d" % (owner, count))

    header_print("Inactive (%s) owners with the most files:" % since)
    print_count = 0
    for owner, count in files_per_owner_counter.most_common():
        if owner == "*":
            continue
        if print_count > 60:
            break
        if owner not in active_reviewers:
            mail_filtered_print("%s\t%d" % (owner, count))
            print_count += 1

    if False:
        header_print("Owners with the least files:")
        mail_filtered_print(
            list(reversed(files_per_owner_counter.most_common()))[:20])

    if False:
        owners_per_file_counter = get_files_with_owner_counts(owners_per_file)
        header_print("Files with the most owners:")
        print_count = 0
        for file_or_dir, count in owners_per_file_counter.most_common():
            if count < 10000: # Fewer than "everyone".
                print("%s\t%d" % (file_or_dir, count))
                print_count += 1
                if print_count == 20:
                    break

        header_print("Files/directories with the fewest owners:")
        mail_filtered_print(
            list(reversed(owners_per_file_counter.most_common()))[:50])

    active_owners_per_file_counter = get_files_with_owner_counts(
        owners_per_file, active_reviewers)
    header_print("Files with the highest number of active (%s) owners:" % since)
    print_count = 0
    for file_or_dir, count in active_owners_per_file_counter.most_common():
        if print_count >= 5 and count != prev_count:
            break
        if count >= 10000: # This means "everyone".
            continue
        parent = os.path.dirname(file_or_dir)
        prev_count = count
        if (parent in active_owners_per_file_counter and
            active_owners_per_file_counter[parent] == count):
            # Just print the parent to not clutter the output.
            continue
        print("\t%s\t%d" % (file_or_dir, count))
        print_count += 1

    header_print("Files/directories with the fewest active (%s) owners:" %
                 since)
    fewest_active = list(reversed(
        active_owners_per_file_counter.most_common()))

    print_count = 0
    prev_count = -1
    for file_or_dir, count in fewest_active:
        if print_count >= 100 and count != prev_count or count > 2:
            break
        if count != prev_count:
            print("=== Files/dirs with %d active (%s) owners ===" % (
                count, since))
        parent = os.path.dirname(file_or_dir)
        prev_count = count
        if (parent in active_owners_per_file_counter and
            active_owners_per_file_counter[parent] == count):
            # Just print the parent to not clutter the output.
            continue

        mail_filtered_print("\t%s\t\t\t%r" % (
            file_or_dir,
            _get_active_owners_for_file(
                file_or_dir,
                owners_per_file,
                active_reviewers)))
        print_count += 1

if __name__ == "__main__":
    main()
