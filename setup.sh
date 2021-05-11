#!/bin/bash

pushd "$(dirname $(realpath $0))"

while (( $# )); do
  case "$1" in
    --dev)
      echo "Perfoming dev setup..."
      pip install pre-commit
      pre-commit install
      shift
      ;;
    *)
      break
  esac
done

pip install -r requirements.txt

popd
