{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # Using stable for reliability

  # Use https://search.nixos.org/packages to find packages
  packages = with pkgs; [
    python312             # Base Python 3.12
    python312Packages.pip  # For installing additional Python packages
    python312Packages.fastapi  # For the FastAPI framework
    python312Packages.uvicorn  # ASGI server for FastAPI
    python312Packages.requests  # For API calls (OpenWeather, Gemini)
    python312Packages.scikit-learn  # For Random Forest model
    python312Packages.pandas  # For dataset handling
    python312Packages.joblib  # For loading model files
    python312Packages.python-dotenv  # For environment variable management
    nano                    # Text editor for manual edits
    zip                     # For archiving if needed
  ];

  # Sets environment variables in the workspace
  env = {
    GEMINI_API_KEY = "AIzaSyB3x4u31dwLrgTNMLNeb9LWNAJiurinzfA";  # Replace with your key
    OPENWEATHER_API_KEY = "4761e19fa1d5f0e73042f23050507d45";  # Replace with your key
  };

  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python"  # Python extension for better coding support
    ];

    # Enable previews for the web app
    previews = {
      enable = true;
      previews = {
        web = {
          # Run uvicorn with the FastAPI app
          command = ["uvicorn" "main:app" "--host" "0.0.0.0" "--port" "$PORT"];
          manager = "web";
        };
      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        # Verify or download model/data files (customize this script)
        setup-data = ''
          echo "Checking for model and data files..."
          if [ ! -f "rf_model.joblib" ]; then
            echo "Downloading rf_model.joblib (replace with your download logic)..."
            # Add your download command here (e.g., from Google Cloud Storage)
          fi
          if [ ! -f "updated_india_agri_data.csv" ]; then
            echo "Downloading updated_india_agri_data.csv..."
            # Add your download command here
          fi
          echo "Setup complete!"
        '';
        # Open editors for key files by default
        default.openFiles = [ ".idx/dev.nix" "main.py" "README.md" ];
      };
      # Runs when the workspace is (re)started
      onStart = {};
    };
  };
}

