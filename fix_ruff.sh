sed -i 's/from eag.source.python.transformations.errors import TransactionError//' src/eag/source/__init__.py
sed -i 's/raise ValueError(f"Could not get descriptor for {class_name}: {e}")/raise ValueError(f"Could not get descriptor for {class_name}: {e}") from e/' src/eag/source/python/transformations/catalog.py
sed -i 's/from eag.source.python.transformations.edits import TextEdit  # Re-export for compatibility//' src/eag/source/python/transformations/models.py
sed -i 's/with pytest.raises(Exception):/with pytest.raises(Exception):/' tests/test_semantic_transformations.py
sed -i 's/with pytest.raises(Exception):/with pytest.raises(Exception):/' tests/test_transformation_platform.py
