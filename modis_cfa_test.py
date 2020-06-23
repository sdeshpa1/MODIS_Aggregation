from MODIS import *
import time
import glob
import xarray as xr

if __name__ == '__main__':
    M06_dir_path = 'X'
    M03_dir_path = 'Y'
    M03_dir, M06_dir = getInputDirectories(M06_dir_path,M03_dir_path)

    M03_files = sorted(glob.glob(M03_dir + "MYD03.A2008*"))
    M06_files = sorted(glob.glob(M06_dir + "MYD06_L2.A2008*"))
    t0 = time.time()
    # # calculate cloud fraction
    # cf = calculateCloudFraction(M03_files, M06_files)
    # # calculate execution time
    # t1 = time.time()
    # total = t1 - t0
    # print("total execution time (Seconds):" + str(total))
    # # display the output
    # displayOutput(xr.DataArray(cf))
