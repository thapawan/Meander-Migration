# Curvature-Informed Meander Migration Model (CIMM)

## Project Overview

This repository contains the code and data for a study focused on quantifying and predicting river meander migration. The study introduces a novel, explicitly equation-based framework called the Curvature-Informed Meander Migration Model (CIMM). CIMM models meander migration as a function of key fluvial processes. This approach develops a system of differential equations that govern the lateral migration of a river's centerline, integrating key factors such as local channel curvature, bank erodibility, and a probabilistic component.

The study applies CIMM to the Yazoo River in Mississippi, USA, using multi-temporal Landsat imagery processed in Google Earth Engine (GEE). The results demonstrate CIMM's ability to simulate observed meander migration patterns, offering a more mechanistic understanding of channel evolution compared to purely geometric methods.

## Key Features

* **Curvature-Informed Meander Migration Model (CIMM):** A novel, equation-based framework for modeling river meander migration.
* **Integration of Fluvial Processes:** Incorporates key factors such as local channel curvature, bank erodibility, and hydraulic variables.
* **Application to Yazoo River:** Demonstrates the model's effectiveness in a real-world case study.
* **Use of Remote Sensing and GEE:** Utilizes multi-temporal Landsat imagery and the Google Earth Engine platform for efficient data processing and analysis.
* **Medial Axis Transform (MAT):** Employs MAT for accurate extraction of river channel centerlines.
* **Quantitative Validation:** The model's predictions were validated against observed channel positions using metrics such as root mean square error (RMSE) and Hausdorff distance.

## Table of Contents

* [Project Overview](#project-overview)
* [Key Features](#key-features)
* [Table of Contents](#table-of-contents)
* [Installation](#installation)
* [Usage](#usage)
* [Data](#data)
* [Dependencies](#dependencies)
* [Contributing](#contributing)
* [License](#license)
* [Citations](#citations)
* [Figures and Tables](#figures-and-tables)

## Installation

To replicate the study, you will need access to the Google Earth Engine platform and ensure you have the necessary dependencies installed.

1.  **Google Earth Engine Account:** You will need a Google Earth Engine account to run the code. You can sign up for a free account on the [Google Earth Engine website](https://earthengine.google.com/).

2.  **Software Dependencies:** The code is written in JavaScript and runs within the Google Earth Engine environment. No local installation is required to run the primary analysis.

## Usage

The core of the analysis is performed within the Google Earth Engine Code Editor. The main script performs the following steps:

1.  **Data Acquisition:** Multi-temporal Landsat imagery is acquired using GEE.
2.  **Binary Image Creation:** The Modified Normalized Difference Water Index (MNDWI) and Otsu's thresholding are used to create binary images representing water bodies.
3.  **Centerline Extraction:** The Medial Axis Transform (MAT) is applied to extract river channel centerlines.
4.  **Meander Migration Analysis:** The CIMM model is applied to quantify meander migration.
5.  **Validation:** The model's predictions are validated against observed channel positions using metrics such as root mean square error (RMSE) and Hausdorff distance.
6.  **Export:** Results, including binary images and centerlines, can be exported from GEE.

## Data

The study uses the following data:

* **Landsat Imagery:** Multi-temporal Landsat imagery is used to track the evolution of the Yazoo River over time.  The specific collection used is Landsat Collection 2.
* **Yazoo River Shapefile:** A shapefile defining the study area (Yazoo River) is used to clip the imagery and focus the analysis.  This is obtained from the USGS/WBD.

## Dependencies

The primary dependency is the Google Earth Engine platform. The code is designed to run within the GEE environment, leveraging its vast data archive and processing capabilities.

## Contributing

Contributions to this project are welcome. If you would like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Commit your changes.
4.  Push to the branch.
5.  Submit a pull request.

## License

\[Specify the license under which the code and data are released.  For example, you might use the MIT License, Apache 2.0 License, or GPL 3.0 License.]

## Citations

\[Include citations for any relevant publications or datasets used in the study.  Here's an example, and you should add the correct citation when available.  Use BibTeX format if possible.  Also include a citation for the repository, when available.]

1.  Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article. *Title of Journal*, *Volume*(Issue), Pages. DOI.

## Figures and Tables

### Figure 1: Workflow Diagram

\[A figure should be inserted here illustrating the workflow:

* Panel a: Example Landsat image
* Panel b: Binary image derived from MNDWI and Otsu's thresholding
* Panel c: Centerline extracted using MAT
* Panel d: Meander migration analysis using CIMM, showing predicted and observed channel positions]

### Table 1: Overall Meander Migration Rates for the Yazoo River

| River Name   | Time Period           | Migration Rate (m/year) |
| :----------- | :-------------------- | :---------------------- |
| Yazoo River | \[Start Year\]-\[End Year\] | \[Value]                |

*Note: Specific values will be included upon completion of the analysis. To maintain anonymity, the table presents the general format.*

