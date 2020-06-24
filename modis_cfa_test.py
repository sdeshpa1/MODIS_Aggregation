from MODIS import *
import time
import glob
import xarray as xr

if __name__ == '__main__':
    M06_dir_path = './resources/data/sample_input_data/MYD06_L2/*.hdf'
    M03_dir_path = './resources/data/sample_input_data/MYD03/*.hdf'

    M03_dir, M06_dir = getInputDirectories(M06_dir_path, M03_dir_path)

    M03_files = sorted(glob.glob(M03_dir_path))
    M06_files = sorted(glob.glob(M06_dir_path))
    print(M03_files)
    print(M06_files)
    t0 = time.time()
    #calculate cloud fraction
    cf = calculateCloudFraction(M03_files, M06_files)
    #print("Cloud Fraction : {0}".format(cf))
    # # calculate execution time
    # t1 = time.time()
    # total = t1 - t0
    # print("total execution time (Seconds):" + str(total))
    # # display the output
    # displayOutput(xr.DataArray(cf))
