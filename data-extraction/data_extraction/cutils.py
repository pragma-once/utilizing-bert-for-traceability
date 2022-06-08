import ctypes
import os
import platform

current_dir = os.path.dirname(os.path.realpath(__file__))

diff_library = None

if platform.system() == "Windows":
    diff_library_path = os.path.join(current_dir, "clib/diff.dll")
else:
    diff_library_path = os.path.join(current_dir, "clib/diff.so")

if os.path.exists(diff_library_path):
    try:
        diff_library = ctypes.cdll.LoadLibrary(diff_library_path)
    except:
        pass

def diff(old_items_sha256: list[bytes], new_items_sha256: list[bytes]):
    """
    Have to check if diff_library != None before using.
    """
    old_arr = (ctypes.c_byte * (len(old_items_sha256) * 32))()
    old_arr[:] = [b for item in old_items_sha256 for b in item]
    new_arr = (ctypes.c_byte * (len(new_items_sha256) * 32))()
    new_arr[:] = [b for item in new_items_sha256 for b in item]
    removed_items_output = (ctypes.c_int64 * len(old_items_sha256))()
    #removed_items_output[:] = [-1 for i in range(len(old_items_sha256))]
    added_items_output = (ctypes.c_int64 * len(new_items_sha256))()
    #added_items_output[:] = [-1 for i in range(len(new_items_sha256))]
    diff_library.diff(old_arr, new_arr, len(old_items_sha256), len(new_items_sha256), removed_items_output, added_items_output)
    return {
        "removed_items": [item for item in removed_items_output if item != -1],
        "added_items": [item for item in added_items_output if item != -1]
    }

def main():
    import hashlib
    a = "abcdef"
    b = "aacdf"
    print("Test: diff of " + a + " " + b)
    d = diff([hashlib.sha256(ch.encode("utf-8")).digest() for ch in a], [hashlib.sha256(ch.encode("utf-8")).digest() for ch in b])
    print("Removed items:")
    print(d["removed_items"])
    print("Added items:")
    print(d["added_items"])

if __name__ == "__main__":
    main()
