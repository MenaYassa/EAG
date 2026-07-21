"""Transformation catalog for EAG."""

from eag.source.python.transformations.descriptor import TransformationDescriptor
from eag.source.python.transformations.protocol import Transformation


class TransformationCatalog:
    """Catalog of registered transformations."""

    def __init__(self):
        self._transformations: dict[str, type[Transformation]] = {}
        self._descriptors: dict[str, TransformationDescriptor] = {}

    def register(self, transformation_class: type[Transformation]) -> None:
        """Register a transformation class."""
        # Get the class name for error messages
        class_name = getattr(transformation_class, "__name__", str(transformation_class))

        # Check if the class has a descriptor property
        if not hasattr(transformation_class, "descriptor"):
            raise ValueError(f"Transformation {class_name} has no descriptor")

        # Get the descriptor from the class
        try:
            # Try to get descriptor without instantiating if it's a class property
            descriptor = getattr(transformation_class, "descriptor", None)

            # If descriptor is a property, we need to create an instance
            if isinstance(descriptor, property):
                # Try to create instance with minimal parameters
                try:
                    # Try to instantiate without parameters
                    instance = transformation_class()
                except TypeError:
                    # Try with empty strings for common parameters
                    try:
                        instance = transformation_class("", "")
                    except TypeError:
                        # Try with default parameters
                        instance = transformation_class()

                descriptor = instance.descriptor
            elif callable(descriptor):
                # If it's a method, call it
                try:
                    instance = transformation_class()
                except TypeError:
                    try:
                        instance = transformation_class("", "")
                    except TypeError:
                        instance = transformation_class()
                descriptor = descriptor(instance)

            # If descriptor is None, create a default one
            if descriptor is None:
                raise ValueError(f"Descriptor is None for {class_name}")

        except Exception as e:
            raise ValueError(f"Could not get descriptor for {class_name}: {e}")

        # Ensure descriptor has a name
        if not hasattr(descriptor, "name"):
            raise ValueError(f"Descriptor for {class_name} has no 'name' attribute")

        if descriptor.name in self._transformations:
            raise ValueError(f"Transformation '{descriptor.name}' already registered")

        self._transformations[descriptor.name] = transformation_class
        self._descriptors[descriptor.name] = descriptor

    def find(self, name: str) -> type[Transformation]:
        """Find a transformation by name."""
        if name not in self._transformations:
            raise KeyError(f"Transformation '{name}' not found in catalog")
        return self._transformations[name]

    def available(self) -> tuple[str, ...]:
        """Get available transformation names."""
        return tuple(self._transformations.keys())

    def get_descriptor(self, name: str) -> TransformationDescriptor:
        """Get descriptor for a transformation."""
        return self._descriptors[name]
