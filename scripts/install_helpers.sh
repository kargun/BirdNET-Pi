# this should only contain functions and assignments, ie source install.sh should not have side effects.

get_tf_whl () {
  BASE_URL=https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.1/

  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
  case "${PY_VERSION}" in
    39)
      WHL=tflite_runtime-2.11.0-cp39-none-linux_aarch64.whl
      ;;
    310)
      WHL=tflite_runtime-2.11.0-cp310-none-linux_aarch64.whl
      ;;
    311)
      WHL=tflite_runtime-2.11.0-cp311-cp311-linux_aarch64.whl
      ;;
    *)
      echo "No tflite version found"
      WHL=''
      ;;
  esac
  if [ -n "$WHL" ]; then
    {
      curl -L -o $HOME/BirdNET-Pi/$WHL $BASE_URL$WHL
      sed "s/tflite_runtime.*/$WHL/" $HOME/BirdNET-Pi/requirements.txt > requirements_custom.txt
    }
  fi
}