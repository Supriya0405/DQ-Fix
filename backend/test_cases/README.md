# Test Cases Folder

This folder contains sample test cases for the DQ-Fix data quality dashboard.

## 📁 Contents

- **sample_test_case.py** - Comprehensive test suite demonstrating testing approach for DQ-Fix

## 🧪 Test Categories

The sample test case file includes the following test suites:

### 1. Data Loading and Basic Operations
- Dataset loading verification
- Dataset summary calculation
- Data quality metrics

### 2. Rule Engine Functionality
- Rule loading and management
- Rule summary generation
- Column-based rule filtering

### 3. Validation Engine
- Validation execution
- Failure detection
- Result filtering and summarization

### 4. AI Analysis Integration
- LLM client availability
- Failure analysis
- Root cause detection

### 5. Agent Loop
- Agent initialization
- Agent execution workflow
- Iteration tracking

### 6. Health Score Calculation
- Health score computation
- Score improvement tracking
- Data quality metrics

### 7. End-to-End Integration
- Complete workflow testing
- Multi-rule validation scenarios
- Integration testing

### 8. Edge Cases
- Empty dataframe handling
- Missing column handling
- All-null column handling
- Error scenarios

## 🚀 How to Run Tests

### Run all test cases:
```bash
cd test_cases
python sample_test_case.py
```

### Run with pytest:
```bash
cd test_cases
pytest sample_test_case.py -v
```

### Run specific test suite:
```bash
cd test_cases
pytest sample_test_case.py::TestValidationEngine -v
```

### Run specific test case:
```bash
cd test_cases
pytest sample_test_case.py::TestValidationEngine::test_validation_execution -v
```

## 📝 Test Case Naming Convention

Test cases follow the naming convention: `TC-{CATEGORY}-{NUMBER}`

Examples:
- `TC-DATA-001` - Data loading test
- `TC-VAL-001` - Validation test
- `TC-AI-001` - AI analysis test
- `TC-E2E-001` - End-to-end integration test

## 🔧 Customization

To create your own test cases:

1. Copy `sample_test_case.py` as a template
2. Modify the fixtures for your specific data
3. Add new test classes and methods
4. Follow the existing naming conventions
5. Include docstrings explaining test steps

## 📊 Test Coverage

The sample test cases cover:
- ✅ Data loading and validation
- ✅ Rule engine operations
- ✅ Validation engine functionality
- ✅ AI analysis integration (mocked)
- ✅ Agent loop execution (mocked)
- ✅ Health score calculation
- ✅ End-to-end workflows
- ✅ Edge cases and error handling

## 🛠️ Requirements

- Python 3.8+
- pytest
- pandas
- numpy

Install requirements:
```bash
pip install pytest pandas numpy
```

## 📖 Documentation

Each test case includes:
- Test case ID
- Description
- Step-by-step test procedure
- Expected results

## 🤝 Contributing

When adding new test cases:
1. Follow the existing structure
2. Use descriptive test names
3. Include comprehensive docstrings
4. Test both success and failure scenarios
5. Update this README with new test categories

## 🔍 Debugging

To debug test failures:
```bash
cd test_cases
pytest sample_test_case.py -v -s --tb=long
```

For more detailed output:
```bash
cd test_cases
pytest sample_test_case.py -vv
```

## 📈 Continuous Integration

These test cases can be integrated into CI/CD pipelines:
- GitHub Actions
- GitLab CI
- Jenkins
- Azure DevOps

Example GitHub Actions workflow:
```yaml
name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pandas numpy
      - name: Run tests
        run: |
          cd test_cases
          pytest sample_test_case.py -v
```

## 📞 Support

For questions or issues with test cases, please refer to the main project documentation or create an issue in the repository.
