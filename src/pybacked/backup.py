import os.path
import pybacked.diff
import pybacked.logging
import pybacked.restore
import pybacked.zip_handler
import time


def backup(config):
    """
    Perform a backup with the given configuration

    :param config: The configuration for the backup. All the needed data
        should be stored inside a Configuration class object.
    :type config: Configuration
    """
    diffcache = pybacked.diff.collect(config.storage, config.archive,
                                      config.diff_algorithm,
                                      config.hash_algorithm, )
    file_dict = create_filedict(diffcache)
    archname = get_new_archive_name(config.archive)
    arch_full_path = os.path.abspath(config.archive + "/" + archname)

    # write files to archive
    pybacked.zip_handler.create_archive(arch_full_path, file_dict,
                                        config.compression_algorithm,
                                        config.compresslevel)

    # write log to archive
    pybacked.logging.write_log(diffcache, arch_full_path,
                               config.compression_algorithm,
                               config.compresslevel)

    # write metadata.json
    timestamp = time.time()
    metadata = pybacked.logging.MetadataContainer(timestamp=timestamp)
    pybacked.logging.write_metadata(metadata, arch_full_path,
                                    config.compression_algorithm,
                                    config.compresslevel)


def create_filedict(diffcache, subdir=""):
    """
    Create a dictionary of filepath, filename key-value pairs for each enty
    (and subdirectory-entry) in the DiffCache. Here the filename refers to the
    name that the file is given in the archive and is derived from the
    basename of the path.

    :param diffcache: The DiffCache from which the dictionary should be
        created.
    :type diffcache: DiffCache
    :param subdir: A subdirectory prefix, which will be prepended to the
        filenames. This is mainly used for recursion.
    :type subdir: str
    :return: Returns a dictionary of filepath, filename key-value pairs which,
        can be passed to zip_handler.archive_write().
    :rtype: dict
    """
    dictionary = {}
    for element in diffcache:
        if element[2]:
            sub_path = subdir + os.path.basename(element[0]) + "/"
            sub_dict = create_filedict(element[1], subdir=sub_path)
            for path, filename in sub_dict.items():
                dictionary[path] = filename
        else:
            dictionary[element[0]] = subdir + os.path.basename(element[0])
    return dictionary


def get_new_archive_name(archive_dir):
    """
    Checks for existing archives and returns the name of the next archive to
    be created.

    :param archive_dir: The directory in which the archives are located
    :type archive_dir: str
    :return: Returns the name, that the next archive should have
    :rtype: str
    """
    archive_list = pybacked.restore.get_archive_list(archive_dir)
    last_archive = os.path.basename(archive_list[0])
    archive_number = int(last_archive.split('.')[0][-1]) + 1
    archive_name = "arch" + str(archive_number) + ".zip"
    return archive_name
