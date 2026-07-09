// main.js (Complete, Final, and Corrected Version)

function getUnionOfResultKeys(results) {
  const keysSet = new Set();
  results.forEach(r => {
    if (r.result) {
      Object.keys(r.result).forEach(key => keysSet.add(key));
    }
  });
  return Array.from(keysSet);
}

// Global variable to store all generic names.
window.genericNames = [];

// Function to populate the generic datalist with a given array of names.
function populateGenericDatalist(names) {
  const genericList = document.getElementById("generic-list");
  genericList.innerHTML = ""; // Clear existing options.
  names.forEach(name => {
    let option = document.createElement("option");
    option.value = name;
    genericList.appendChild(option);
  });
}

// On page load, fetch all generic names from the backend.
window.addEventListener("load", function() {
  fetch("/generic_names")
    .then(response => response.json())
    .then(data => {
      window.genericNames = data.generic_names;
      populateGenericDatalist(window.genericNames);
    })
    .catch(error => console.error("Error fetching generic names:", error));
});

// Fetch disease suggestions when generic input changes.
document.getElementById("generic").addEventListener("input", function(event) {
  const inputValue = event.target.value;
  const filtered = window.genericNames.filter(name => name.toLowerCase().includes(inputValue.toLowerCase()));
  populateGenericDatalist(filtered);
  
  if (inputValue.trim() !== "") {
    fetch("/disease_names?generic=" + encodeURIComponent(inputValue))
      .then(response => response.json())
      .then(data => {
        const diseaseList = document.getElementById("disease-list");
        diseaseList.innerHTML = "";
        data.disease_names.forEach(name => {
          let option = document.createElement("option");
          option.value = name;
          diseaseList.appendChild(option);
        });
      })
      .catch(error => console.error("Error fetching disease names:", error));
  }
});

const MAX_ROWS_DISPLAYED = 1000;

// --- Single Medication Form Submission with ADVANCED User-Friendly Report ---
document.getElementById("single-medication-form").addEventListener("submit", function (event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  let data = Object.fromEntries(formData.entries());

  // Standardize the values
  data.age_unit = data.age_unit ? data.age_unit.toUpperCase() : "";
  data.administration = data.administration ? data.administration.toUpperCase() : "";
  data.dose_unit = data.dose_unit ? data.dose_unit : "mg";

  fetch("/validate_medication/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) {
        // Try to get a more detailed error from the server's response
        return response.json().then(errorData => {
            const detail = errorData.detail || JSON.stringify(errorData);
            throw new Error(`HTTP error! Status: ${response.status} - ${detail}`);
        }).catch(() => {
            // If the response isn't JSON, use the status text
            throw new Error(`HTTP error! Status: ${response.status}`);
        });
    }
    return response.json();
  })
  .then(responseData => {
    const result = responseData.validation_result;
    const resultContainer = document.getElementById("single-result");
    const resultTextElement = document.getElementById("single-result-text");

    // --- THIS IS THE CHANGE ---
    // Get the dose unit from the user's input to use in the message
    const doseUnit = data.dose_unit || 'units';
    // --- END OF CHANGE ---

    let outputHtml = ``;
    let overallStatus = "✅ Prescription appears appropriate.";
    let hasError = false;

    // Check Normal Dose
    if (result.normal_dose_result && result.normal_dose_result !== 'yes') {
        hasError = true;
        let doseStatusColor = 'orange';
        if (result.normal_dose_result.toLowerCase().includes('overdose') || result.normal_dose_result.toLowerCase().includes('underdose')) {
            doseStatusColor = 'red';
        }
        outputHtml += `<h4>Normal Dose Status</h4>`;
        outputHtml += `<p><strong>Result:</strong> <span style="color: ${doseStatusColor}; font-weight: bold;">${result.normal_dose_result}</span></p>`;
        outputHtml += `<p><strong>Details:</strong> ${result.normal_dose_message}</p>`;
        
        // --- THIS IS THE CHANGE ---
        if (result.dose_excess) {
            outputHtml += `<p><strong>Dose Excess:</strong> <span style="color: red; font-weight: bold;">${result.dose_excess.toFixed(2)} ${doseUnit}</span></p>`;
        }
        if (result.dose_deficit) {
            outputHtml += `<p><strong>Dose Deficit:</strong> <span style="color: red; font-weight: bold;">${result.dose_deficit.toFixed(2)} ${doseUnit}</span></p>`;
        }
        // --- END OF CHANGE ---

    } else {
        outputHtml += `<h4>Normal Dose Status</h4>`;
        outputHtml += `<p><strong>Result:</strong> <span style="color: green; font-weight: bold;">Appropriate</span></p>`;
    }
    
    outputHtml += `<hr>`;

    // Check Renal Dose
    if (result.renal_dose_result) {
        outputHtml += `<h4>Renal Dose Adjustment</h4>`;
        let renalColor = 'green';
        if (result.renal_dose_result.toLowerCase().includes("overdose") || result.renal_dose_result.toLowerCase().includes("error") || result.renal_dose_result.toLowerCase().includes("not recommended")) {
            renalColor = 'red';
        } else if (result.renal_dose_result.toLowerCase().includes("not found") || result.renal_dose_result.toLowerCase().includes("not available")) {
            renalColor = 'orange';
        }
        
        outputHtml += `<p><strong>Result:</strong> <span style="color: ${renalColor}; font-weight: bold;">${result.renal_dose_result}</span></p>`;
        outputHtml += `<p><strong>Details:</strong> ${result.renal_dose_message}</p>`;
        
        // --- THIS IS THE CHANGE ---
        if (result.renal_dose_exceeded_amount) {
            outputHtml += `<p><strong>Exceeded Amount:</strong> <span style="color: red; font-weight: bold;">${result.renal_dose_exceeded_amount.toFixed(2)} ${doseUnit}</span></p>`;
        }
        // --- END OF CHANGE ---

        if(renalColor === 'red') hasError = true;
    }

    outputHtml += `<hr>`;

    // Pregnancy Risk
    outputHtml += `<h4>Other Information</h4>`;
    const risk = result.pregnancy_risk_category || 'Unknown';
    let riskColor = 'black';
    if (['D', 'X'].includes(risk)) {
        riskColor = 'red';
    } else if (risk === 'C') {
        riskColor = 'orange';
    }
    outputHtml += `<p><strong>Pregnancy Risk Category:</strong> <span style="color: ${riskColor}; font-weight: bold;">${risk}</span></p>`;
    
    // Set overall status
    if (hasError) {
        overallStatus = "⚠️ Attention Required. Please review the details below.";
    }
    
    // Prepend the overall status to the beginning of the output
    outputHtml = `<h3>Overall Status: ${overallStatus}</h3><hr>` + outputHtml;

    resultTextElement.innerHTML = outputHtml;
    resultContainer.style.display = "block";
  })
  .catch(error => {
    document.getElementById("single-result-text").textContent = `❌ ${error.message}`;
    document.getElementById("single-result").style.display = "block";
  });
});


// --- Batch Medication Form Submission Logic (Remains the same) ---
document.getElementById("batch-medication-form").addEventListener("submit", function (event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const fileInput = document.getElementById("csv-file");
  if (fileInput.files.length === 0) {
    alert("Please select a CSV file to upload.");
    return;
  }
  formData.set("file", fileInput.files[0]);
  const statusElem = document.getElementById("upload-status");
  statusElem.textContent = "Uploading and processing file, please wait...";
  statusElem.style.display = "block";

  fetch("/validate_batch/", {
    method: "POST",
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(error => { throw new Error(error.detail || "An unknown error occurred.") });
    }
    return response.json();
  })
  .then(data => {
    if (!("input_data" in data) || !("results" in data)) {
      throw new Error("Invalid response from server: missing input_data or results");
    }
    window.fullResults = data.results;
    window.fullInputData = data.input_data;
    displayResults(data.results, data.input_data);
    document.getElementById("download-button").style.display = "block";
  })
  .catch(error => {
    alert(`❌ Error: ${error.message}`);
  })
  .finally(() => {
    statusElem.style.display = "none";
  });
});

// Function to display batch results with color-coding
function displayResults(results, inputData) {
  const table = document.getElementById("result-table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");
  
  thead.innerHTML = "";
  tbody.innerHTML = "";
  
  if (results.length === 0 || inputData.length === 0) return;
  
  const inputColumns = Object.keys(inputData[0]);
  let resultColumns = getUnionOfResultKeys(results);
  const expectedOrder = [
    "pregnancy_risk_category", "normal_dose_result", "normal_dose_message",
    "dose_excess", "dose_deficit", "renal_dose_result", "renal_dose_message",
    "renal_dose_exceeded_amount"
  ];
  resultColumns = expectedOrder.filter(key => resultColumns.includes(key))
    .concat(resultColumns.filter(key => !expectedOrder.includes(key)));
  
  const allColumns = ["S.No", ...inputColumns, ...resultColumns];
  
  const headerRow = document.createElement("tr");
  allColumns.forEach(col => {
    const th = document.createElement("th");
    th.textContent = col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  
  let displayCount = Math.min(inputData.length, MAX_ROWS_DISPLAYED);
  
  for (let i = 0; i < displayCount; i++) {
    const inputRow = inputData[i];
    const resultRow = results[i].result || {};
    const tr = document.createElement("tr");
    
    const indexTd = document.createElement("td");
    indexTd.textContent = i + 1;
    tr.appendChild(indexTd);
    
    inputColumns.forEach(col => {
      const td = document.createElement("td");
      td.textContent = inputRow[col] ?? "N/A";
      tr.appendChild(td);
    });
    
    resultColumns.forEach(col => {
      const td = document.createElement("td");
      const value = resultRow[col] ?? "N/A";
      td.textContent = value;
      
      if (col === 'normal_dose_result' || col === 'renal_dose_result') {
          const statusClass = 'status-' + String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
          td.classList.add(statusClass);
      }
      
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
}

// Function to download results as CSV
function downloadResultsAsCSV(results, inputData) {
    // This function remains the same, no changes needed here.
    if (results.length === 0 || inputData.length === 0) return;
    const inputColumns = Object.keys(inputData[0]);
    let resultColumns = getUnionOfResultKeys(results);
    const expectedOrder = [
      "pregnancy_risk_category", "normal_dose_result", "normal_dose_message",
      "dose_excess", "dose_deficit", "renal_dose_result", "renal_dose_message",
      "renal_dose_exceeded_amount"
    ];
    resultColumns = expectedOrder.filter(key => resultColumns.includes(key))
      .concat(resultColumns.filter(key => !expectedOrder.includes(key)));

    const allColumns = [...inputColumns, ...resultColumns];
    let csvContent = allColumns.join(",") + "\n";

    for (let i = 0; i < inputData.length; i++) {
      const inputRow = inputData[i];
      const resultRow = results[i].result || {};
      let rowValues = [];
      inputColumns.forEach(col => {
        rowValues.push(`"${String(inputRow[col] ?? "").replace(/"/g, '""')}"`);
      });
      resultColumns.forEach(col => {
        const val = String(resultRow[col] ?? "").replace(/"/g, '""');
        rowValues.push(`"${val}"`);
      });
      csvContent += rowValues.join(",") + "\n";
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "validation_results.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

document.getElementById("download-button").addEventListener("click", function() {
  if (window.fullResults && window.fullInputData) {
    downloadResultsAsCSV(window.fullResults, window.fullInputData);
  } else {
    alert("No results available for download.");
  }
});
