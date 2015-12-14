#!/usr/bin/python

# This script will generate a permutative batch job script on Cori for
# the mt branch of p3dfft.
#
# More specifically, the generated batch script will test for correctness
# of all tests (under sample/FORTRAN and sample/C) for each configuration
# of p3dfft-mt available (see below). Because we only care about correctness,
# 1 node with 16 cores will be used with four dimensions: 4x4, 1x16, 16x1.
# NUMTHREADS can be set to vary the number of OMP threads.
#
# The p3dfft-mt directories need to be in the current working directory from which
# this script is executed, named 'p3dfft0-mt' to 'p3dfftX-mt' (use the configure-mt.py
# script for that).
#
# The jobs/ directory needs to exist in the current working directory. This
# is where all batch job files are written to.

import os
import re

TOTALTASKS = 16
NUMMPITASKS = 8  # used for dims
NUMTHREADS = 2   # env var OMP_NUM_THREADS

assert (TOTALTASKS == NUMMPITASKS * NUMTHREADS)

# Factorisation helper function
def factors(n):
    return set(reduce(list.__add__,
        ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

    # Open batch job file to be written to.
batchf = open('jobs/cori_permutative-mt.sh', 'w')

# Write SBATCH header commands.
batchf.write('#!/bin/bash\n')
batchf.write('#SBATCH -J p3dfft-mt\n')
batchf.write('#SBATCH -o out/out.%j\n')
batchf.write('#SBATCH -e out/err.%j\n')
batchf.write('#SBATCH -p debug\n')
batchf.write('#SBATCH --mail-user=jytang@ucsd.edu\n')
batchf.write('#SBATCH --mail-type=ALL\n')
batchf.write('#SBATCH -t 00:30:00\n')
batchf.write('\n')
batchf.write('export OMP_NUM_THREADS=' + str(NUMTHREADS) + '\n')

basedir = os.getcwd()

# Get all p3dfft config directories
p3dfft_dirs = next(os.walk('.'))[1]
pattern = re.compile('p3dfft\d+-mt$')
p3dfft_dirs = sorted(filter(pattern.match, p3dfft_dirs))

# Get all test names using first directory
f_dir = os.path.join(p3dfft_dirs[0], 'sample/FORTRAN')
c_dir = os.path.join(p3dfft_dirs[0], 'sample/C')

pattern = re.compile('test_\S+_[cf].x')
f_test_files = filter(pattern.match, next(os.walk(f_dir))[2])
c_test_files = filter(pattern.match, next(os.walk(c_dir))[2])

# Get full paths to tests in all dirs
all_tests = []
for d in p3dfft_dirs:
    f_dir = os.path.join(d, 'sample/FORTRAN')
    c_dir = os.path.join(d, 'sample/C')
    for test in f_test_files:
        all_tests.append(os.path.join(f_dir, test))
    for test in c_test_files:
        all_tests.append(os.path.join(c_dir, test))

# Calculate dims
all_dims = []
facs = sorted(factors(NUMMPITASKS))
if (len(facs) % 2 == 0):
    # take the two factors in the middle
    all_dims.append("'" + str(facs[len(facs)/2-1]) + " " + str(facs[len(facs)/2]) + "'")
else:
    # perfect square, take the factor in the middle
    all_dims.append("'" + str(facs[len(facs)/2]) + " " + str(facs[len(facs)/2]) + "'")
all_dims.append("'" + str(facs[len(facs)-1]) + " " + str(facs[0]) + "'")
all_dims.append("'" + str(facs[0]) + " " + str(facs[len(facs)-1]) + "'")
#all_dims = ["'4 4'", "'16 1'", "'1 16'", "'1 1'"]

# Run all tests for all dims
for test in all_tests:
    if "cheby" in test:
        batchf.write("echo '128 128 129 2 1' > stdin\n")
    elif "many" in test:
        batchf.write("echo '128 128 128 2 5 1' > stdin\n")
    else:
        batchf.write("echo '128 128 128 2 1' > stdin\n")
    for dims in all_dims:
        # write dims
        batchf.write("echo " + dims + " > dims\n")
        # run test
        batchf.write("srun -n " + str(NUMMPITASKS) + " -c " + str(NUMTHREADS) + " " + basedir + "/" + test + "\n")
    # 1x1 dims test
    batchf.write("echo '1 1' > dims\n")
    batchf.write("srun -n 1 -c " + str(NUMTHREADS) + " " + basedir + "/" + test + "\n")

# Truncate previous content if any existed.
#batchf.truncate()

# Close the file. Done.
batchf.close()
