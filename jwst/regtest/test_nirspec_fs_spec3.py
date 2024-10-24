from astropy.io.fits.diff import FITSDiff
import pytest
import numpy as np
import os
from gwcs import wcstools

from jwst.stpipe import Step
from stdatamodels.jwst import datamodels


@pytest.fixture(scope="module")
def run_pipeline(rtdata_module):
    """
    Run the calwebb_spec3 pipeline on NIRSpec Fixed-Slit exposures.
    """
    rtdata = rtdata_module

    # Get the ASN file and input exposures
    rtdata.get_asn('nirspec/fs/jw01309-o022_spec3_regtest_asn.json')

    # Run the calwebb_spec3 pipeline; save results from intermediate steps
    args = ["calwebb_spec3", rtdata.input,
            "--steps.outlier_detection.save_results=true",
            "--steps.outlier_detection.save_intermediate_results=true",
            "--steps.resample_spec.save_results=true",
            "--steps.extract_1d.save_results=true"]
    Step.from_cmdline(args)


@pytest.mark.bigdata
@pytest.mark.parametrize("suffix", ["cal", "crf", "s2d", "x1d", "median"])
@pytest.mark.parametrize("source_id,slit_name", [("s000000001","s200a2"), ("s000000021","s200a1"),
    ("s000000023","s400a1"), ("s000000024","s1600a1"), ("s000000025","s200b1")])
def test_nirspec_fs_spec3(run_pipeline, rtdata_module, fitsdiff_default_kwargs, suffix, source_id, slit_name):
    """Test spec3 pipeline on a set of NIRSpec FS exposures."""
    rtdata = rtdata_module

    if suffix == "median":
        output = f"jw01309022001_04102_00001_nrs2_{slit_name}_{suffix}.fits"
        # also ensure drizzled and blot models were created with the correct names
        assert os.path.isfile(output.replace("median", "outlier_s2d"))
        assert os.path.isfile(output.replace("median", "blot"))
    else:
        output = f"jw01309-o022_{source_id}_nirspec_f290lp-g395h-{slit_name}-allslits_{suffix}.fits"
    rtdata.output = output
    rtdata.get_truth(f"truth/test_nirspec_fs_spec3/{output}")

    # Adjust tolerance for machine precision with float32 drizzle code
    if suffix == "s2d":
        fitsdiff_default_kwargs["rtol"] = 1e-2
        fitsdiff_default_kwargs["atol"] = 2e-4

    # Compare the results
    diff = FITSDiff(rtdata.output, rtdata.truth, **fitsdiff_default_kwargs)
    assert diff.identical, diff.report()

    # Check output wavelength array against its own wcs
    if suffix == "s2d":
        tolerance = 1e-03
        dmr = datamodels.open(rtdata.output)

        w = dmr.meta.wcs
        x, y = wcstools.grid_from_bounding_box(w.bounding_box, step=(1, 1), center=True)
        _, _, wave = w(x, y)
        wlr = dmr.wavelength
        assert np.all(np.isclose(wave, wlr, atol=tolerance))
