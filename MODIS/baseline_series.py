#!/usr/bin/env python
# coding:utf8
# -*- coding: utf-8 -*-
"""
Main Program: Run MODIS AGGREGATION IN SERIES WITH FLEXIBLE STATISTICS 

Created on 2019

@author: Jianyu Zheng

V2 Updates: Add statistics for flexible variables

V3 Updates: Add 1d histogram with upper and lower boundaries

V4 Updates: Add 2d histogram by using additional input file

V5 Updates: Refine 1d histogram and 2d histogram to be user-defined intervals 
			Combine the interval with the variable names in onw file. 
            Separate 1d and 2d histogram interval in 2 files with all variables.

V6 Updates: Add the flexible input of sampling rate, polygon region and grid sizes of Lat & Lon

V7 Updates: Change the sampling rate starts from 3 and 4 count from 1 (Here we count from 0 so it starts from 2 and 3). 
			Add the flexible input of data path, date and time period for averaging

V8 Updates: Change histogram count from averaged value to be all pixel values 
			Added scale_factor, add_offset and _Fillvalue as attributes to each variabes.
			Found the problem in reading temperature and fixed it by changing the reading way:
				For netCDF4, the variable is done by (rdval * scale) + offst
				For MODIS HDF4 file, the variable should be done by (rdval-offst)*scale 
				It needs to be reverted from the netCDF4 reading first, then convert it in the way of HDF file.
"""

import os
import sys
import h5py
import timeit
import random
import numpy as np
import pandas as pd
from mpi4py import MPI
from netCDF4 import Dataset
from collections import OrderedDict
from datetime import date, datetime
from dateutil.rrule import rrule, DAILY, MONTHLY


def read_filelist(loc_dir, prefix, yr, day, fileformat):
    # Read the filelist in the specific directory
    str = os.popen("ls " + loc_dir + prefix + yr + day + "*." + fileformat).read()
    fname = np.array(str.split("\n"))
    fname = np.delete(fname, len(fname) - 1)

    return fname


def readEntry(key, ncf):
    # Read the MODIS variables based on User's name list
    rdval = np.array(ncf.variables[key]).astype(np.float)

    # For netCDF4, the variable is done by (rdval * scale) + offst
    # For MODIS HDF4 file, the variable should be done by (rdval-offst)*scale
    # It needs to be reverted from the netCDF4 reading first, then convert it in the way of HDF file.

    # Read the attributes of the variable
    unit = ncf.variables[key].units
    scale = ncf.variables[key].scale_factor
    offst = ncf.variables[key].add_offset
    lonam = ncf.variables[key].long_name
    fillvalue = ncf.variables[key]._FillValue

    rdval[np.where(rdval == fillvalue)] = np.nan

    # Sampling the variable
    rdval = rdval[2::spl_num, 3::spl_num]

    return rdval, lonam, unit, fillvalue, scale, offst


def read_MODIS(varnames, fname1, fname2):
    # Store the data from variables after reading MODIS files
    data = {}

    # Read the Cloud Mask from MYD06 product
    ncfile = Dataset(fname1, 'r')

    # CM1km = readEntry('Cloud_Mask_1km',ncfile)
    # CM1km = np.array(ncfile.variables['Cloud_Mask_1km'])
    # data['CM'] = (np.array(CM1km[:,:,0],dtype='byte') & 0b00000110) >>1

    d06_CM = ncfile.variables['Cloud_Mask_1km'][:, :, 0]
    CM1km = d06_CM[2::spl_num, 3::spl_num]
    data['CM'] = (np.array(CM1km, dtype='byte') & 0b00000110) >> 1
    data['CM'] = data['CM'].astype(np.float)

    # Read the User-defined variables from MYD06 product
    for key in varnames:
        if key == 'cloud_fraction':
            continue  # Ignoreing Cloud_Fraction from the input file
        else:
            data[key], lonam, unit, fill, scale, offst = readEntry(key, ncfile)
            data[key] = (data[key] - offst) / scale
            data[key] = (data[key] - offst) * scale

    ncfile.close()

    # Read the common variables (Latitude & Longitude) from MYD03 product
    ncfile = Dataset(fname2, 'r')
    d03_lat = np.array(ncfile.variables['Latitude'][:, :])
    d03_lon = np.array(ncfile.variables['Longitude'][:, :])
    lat = d03_lat[2::spl_num, 3::spl_num]
    lon = d03_lon[2::spl_num, 3::spl_num]
    attr_lat = ncfile.variables['Latitude']._FillValue
    attr_lon = ncfile.variables['Longitude']._FillValue

    # If the variable is not 1km product, exit and tell the User to reset the variables.
    for key in varnames:
        if key == 'cloud_fraction': continue  # Ignoreing Cloud_Fraction from the input file
        if data[key].shape[0] != lat.shape[0]:
            print("The dimension of varibale '" + key + "' is not match with latitude & longitude.")
            print("Input variables should have 1km resolution.")
            print("Check your varibales.")
            sys.exit()

    # Use _FillValue to remove fill data in lat & lon
    lat[np.where(lat == attr_lat)] = np.nan
    lon[np.where(lat == attr_lat)] = np.nan
    data['CM'][np.where(lat == attr_lat)] = np.nan  # which will not be identified by lines 80-83

    lat[np.where(lon == attr_lon)] = np.nan
    lon[np.where(lon == attr_lon)] = np.nan
    data['CM'][np.where(lon == attr_lon)] = np.nan  # which will not be identified by lines 80-83
    ncfile.close()

    return lat, lon, data


def cal_stats(z, key, grid_data, min_val, max_val, tot_val, count, all_val, all_val_2d, \
              sts_switch, sts_name, intervals_1d, intervals_2d, key_idx):
    # Calculate Statistics pamameters

    # Min and Max
    if sts_switch[0] == True:
        if grid_data[key + '_' + sts_name[0]][z] > min_val:
            grid_data[key + '_' + sts_name[0]][z] = min_val

    if sts_switch[1] == True:
        if grid_data[key + '_' + sts_name[1]][z] < max_val:
            grid_data[key + '_' + sts_name[1]][z] = max_val

    # Total and Count for Mean
    if (sts_switch[2] == True) | (sts_switch[3] == True):
        grid_data[key + '_' + sts_name[2]][z] += tot_val
        grid_data[key + '_' + sts_name[3]][z] += count

    # Standard Deviation
    if sts_switch[4] == True:
        grid_data[key + '_' + sts_name[4]][z] += tot_val ** 2

    # 1D Histogram
    if sts_switch[5] == True:
        bin_interval1 = np.fromstring(intervals_1d[key_idx], dtype=np.float, sep=',')
        if all_val.size == 1:
            all_val = np.array([all_val])
        else:
            hist_idx1 = np.histogram(all_val, bins=bin_interval1)[0]
            grid_data[key + '_' + sts_name[5]][z, :] += hist_idx1
    # for i in range(all_val.size):
    #	hist_idx1 = np.where(bin_interval1 <= all_val[i])[0]
    #	#hist_idx1 = 0 if len(hist_idx1) == 0 else hist_idx1[-1]
    #	#if hist_idx1 > (grid_data[key+'_'+sts_name[5]].shape[1]-1): hist_idx1 = (grid_data[key+'_'+sts_name[5]].shape[1]-1)
    #	grid_data[key+'_'+sts_name[5]][z, hist_idx1] += 1

    # 2D Histogram
    if sts_switch[6] == True:
        bin_interval1 = np.fromstring(intervals_1d[key_idx], dtype=np.float, sep=',')
        bin_interval2 = np.fromstring(intervals_2d[key_idx], dtype=np.float, sep=',')
        if all_val.size == 1:
            all_val = np.array([all_val])
            all_val_2d = np.array([all_val_2d])
        else:
            hist_idx2 = np.histogram2d(all_val, all_val_2d, bins=(bin_interval1, bin_interval2))[0]
            grid_data[key + '_' + sts_name[6] + histnames[key_idx]][z, :, :] += hist_idx2

    # for i in range(all_val_2d.size):
    #	hist_idx1 = np.where(bin_interval1 <= all_val[i])[0]
    #	hist_idx1 = 0 if len(hist_idx1) == 0 else hist_idx1[-1]
    #	if hist_idx1 > (grid_data[key+'_'+sts_name[5]].shape[1]-1): hist_idx1 = (grid_data[key+'_'+sts_name[5]].shape[1]-1)
    #
    #	hist_idx2 = np.where(bin_interval2 <= all_val_2d[i])[0]
    #	hist_idx2 = 0 if len(hist_idx2) == 0 else hist_idx2[-1]
    #	if hist_idx2 > (grid_data[key+'_'+sts_name[6]+histnames[key_idx]].shape[2]-1): hist_idx2 = (grid_data[key+'_'+sts_name[6]+histnames[key_idx]].shape[2]-1)
    #
    #	grid_data[key+'_'+sts_name[6]+histnames[key_idx]][z, hist_idx1,hist_idx2] += 1

    return grid_data


def run_modis_aggre(fname1, fname2, NTA_lats, NTA_lons, grid_lon, grid_lat, gap_x, gap_y, hdfs, \
                    grid_data, sts_switch, varnames, intervals_1d, intervals_2d, var_idx):
    # This function is the data aggregation loops by number of files
    hdfs = np.array(hdfs)
    for j in hdfs:  # range(1):#hdfs:
        print("File Number: {} / {}".format(j, hdfs[-1]))

        # Read Level-2 MODIS data
        lat, lon, data = read_MODIS(varnames, fname1[j], fname2[j])
        CM = data['CM']

        # Restrain lat & lon & variables in the required region
        res_idx = np.where((lat > NTA_lats[0]) & (lat < NTA_lats[1]) & (lon > NTA_lons[0]) & (lon < NTA_lons[1]))
        lat = lat[res_idx]
        lon = lon[res_idx]
        CM = CM[res_idx]

        # Ravel the 2-D data to 1-D array
        lat = lat.ravel()
        lon = lon.ravel()
        CM = CM.ravel()

        key_idx = 0
        for key in varnames:
            if key == 'cloud_fraction':
                CF_key_idx = key_idx
                key_idx += 1
                continue  # Ignoreing Cloud_Fraction from the input file
            data[key] = data[key][res_idx].ravel()
            key_idx += 1

        # Locate the lat lon index into 3-Level frid box
        idx_lon = np.round((lon - NTA_lons[0]) / gap_x).astype(int)
        idx_lat = np.round((lat - NTA_lats[0]) / gap_y).astype(int)

        latlon_index = (idx_lat * grid_lon) + idx_lon

        latlon_index_unique = np.unique(latlon_index)

        # print(lon[0],idx_lon[0],lat[0],idx_lat[0])
        # print(latlon_index_unique.max(),grid_lat*grid_lon)

        for i in np.arange(latlon_index_unique.size):
            # -----loop through all the grid boxes ocupied by this granule------#
            z = latlon_index_unique[i]
            if ((z >= 0) & (z < (grid_lat * grid_lon))):

                # For cloud fraction
                TOT_pix = np.sum(CM[np.where(latlon_index == z)] >= 0).astype(float)
                CLD_pix = np.sum(CM[np.where(latlon_index == z)] <= 1).astype(float)

                # local_data = CM[np.where(latlon_index == z)]
                # if local_data[np.where(np.isnan(local_data) == 0)].size == 0:
                #	print('All NaN is Ture.')

                Fraction = CLD_pix / TOT_pix

                if len(intervals_2d) != 1:
                    pixel_data_2d = data[varnames[var_idx[CF_key_idx]]]
                    ave_val_2d = np.nansum(pixel_data_2d[np.where(latlon_index == z)]).astype(float) / TOT_pix
                else:
                    ave_val_2d = 0

                # Calculate Statistics pamameters
                grid_data = cal_stats(z, "cloud_fraction", grid_data, \
                                      Fraction, Fraction, CLD_pix, TOT_pix, Fraction, ave_val_2d, \
                                      sts_switch, sts_name, intervals_1d, intervals_2d, CF_key_idx)

                # For other variables
                key_idx = 0
                for key in varnames:
                    if key == 'cloud_fraction':  # Ignoreing Cloud_Fraction from the input file
                        key_idx += 1
                        continue
                    pixel_data = data[key]

                    tot_val = np.nansum(pixel_data[np.where(latlon_index == z)]).astype(float)
                    # ave_val = tot_val / TOT_pix
                    all_val = np.array(pixel_data[np.where(latlon_index == z)]).astype(float)
                    max_val = np.nanmax(pixel_data[np.where(latlon_index == z)]).astype(float)
                    min_val = np.nanmin(pixel_data[np.where(latlon_index == z)]).astype(float)

                    # local_data = pixel_data[np.where(latlon_index == z)]
                    # print(local_data.size,z)
                    # print(z,tot_val,max_val,min_val,CLD_pix,TOT_pix)
                    # if local_data[np.where(np.isnan(local_data) == 0)].size == 0:
                    #	print('All NaN is Ture.',key,tot_val,max_val,min_val,CLD_pix,TOT_pix)

                    if len(intervals_2d) != 1:
                        pixel_data_2d = data[varnames[var_idx[key_idx]]]
                        all_val_2d = np.array(pixel_data_2d[np.where(latlon_index == z)]).astype(float)
                    else:
                        all_val_2d = 0

                    # Calculate Statistics pamameters
                    grid_data = cal_stats(z, key, grid_data, \
                                          min_val, max_val, tot_val, CLD_pix, all_val, all_val_2d, \
                                          sts_switch, sts_name, intervals_1d, intervals_2d, key_idx)

                    key_idx += 1

    return grid_data


def addGridEntry(f, name, units, long_name, fillvalue, scale_factor, add_offset, data):
    '''
    f:h5py.File()
    -------------------------------------
    Ex.
    self.addGridEntry(f,'CF','Fraction','Cloud_Fraction',total_cloud_fraction)

    For netCDF4, the variable is done by (rdval * scale) + offst
    For MODIS HDF4 file, the variable should be done by (rdval-offst)*scale
    It needs to be reverted from the netCDF4 reading first, then convert it in the way of HDF file.
    '''
    if (('Histogram_Counts' in name) == True) | (('Jhisto_vs_' in name) == True) | (('Pixel_Counts' in name) == True):
        original_data = data.astype(np.int)
    elif (('Maximum' in name) == True) | (('Minimum' in name) == True):
        tmp_data = data / scale_factor + add_offset
        tmp_data[np.where(np.isinf(tmp_data) == 1)] = fillvalue
        original_data = tmp_data.astype(np.int)
    else:
        tmp_data = data / scale_factor + add_offset
        tmp_data[np.where(np.isnan(tmp_data) == 1)] = fillvalue
        original_data = tmp_data.astype(np.int)

    PCentry = f.create_dataset(name, data=original_data)
    PCentry.dims[0].label = 'lat_bnd'
    PCentry.dims[1].label = 'lon_bnd'
    PCentry.attrs['units'] = np.str(units)
    PCentry.attrs["long_name"] = np.str(long_name)
    PCentry.attrs['_FillValue'] = fillvalue
    PCentry.attrs['scale_factor'] = scale_factor
    PCentry.attrs['add_offset'] = add_offset
