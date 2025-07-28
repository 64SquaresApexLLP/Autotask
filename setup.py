from setuptools import setup, find_packages

setup(
    name="autotask",
    version="1.0.0",
    description="TeamLogic AutoTask System",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "python-multipart>=0.0.6",
        "Pillow>=9.0.0",
        "pytesseract>=0.3.10",
        "opencv-python>=4.5.0",
        "numpy>=1.21.0",
        "schedule>=1.2.0",
        "pandas",
        "pytz",
        "snowflake-connector-python",
        "python-dotenv",
        "scikit-learn",
    ],
)
