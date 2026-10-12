// File: ABIInputDecoder.java
package com.nccgroup.web3decoder.decoder;

import com.fasterxml.jackson.core.type.TypeReference;  // Jackson for ABI JSON parsing
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nccgroup.web3decoder.detection.AbiSelectorBuilder;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.FunctionReturnDecoder;
import org.web3j.abi.TypeReference.StaticArrayTypeReference;
import org.web3j.abi.datatypes.*;
import org.web3j.abi.datatypes.generated.*;
import org.web3j.utils.Numeric;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;

public class ABIInputDecoder {

    private static final String TYPE_TUPLE = "tuple";

    // Method to decode input data given the ABI JSON and the input data
    public static Map<String, Object> decodeInput(String abiJson, String inputData) throws Exception {
        validateMethodInputData(inputData);
        ObjectMapper objectMapper = new ObjectMapper();
        List<Map<String, Object>> abiList = objectMapper.readValue(abiJson, new TypeReference<List<Map<String, Object>>>() {});
    
        // Get the method selector from the input data (first 4 bytes)
        String methodSelector = inputData.substring(0, 10); // 0x + 4 bytes for selector
    
        // Iterate through the ABI to find the function matching the method selector
        for (Map<String, Object> functionDefinition : abiList) {
            if ("function".equals(functionDefinition.get("type"))) {
                // Get function signature
                String functionSignature = buildMethodSignature(functionDefinition);
                String selectorFromABI = buildMethodSelector(functionDefinition);
    
                // If the selector matches, decode the input
                if (methodSelector.equals(selectorFromABI)) {
                    // Get input parameter types from ABI
                    List<org.web3j.abi.TypeReference<?>> inputParameters = getInputParameterTypes(functionDefinition, abiList);
    
                    // Cast inputParameters to List<TypeReference<Type>>
                    @SuppressWarnings("unchecked")
                    List<org.web3j.abi.TypeReference<Type>> typeReferences = (List<org.web3j.abi.TypeReference<Type>>)(List<?>) inputParameters;
    
                    // Strip the method selector from the input data
                    String dataWithoutSelector = inputData.substring(10);
    
                    // Decode the input data
                    List<Type> decodedInput = FunctionReturnDecoder.decode(dataWithoutSelector, typeReferences);
    
                    // Create the output in the desired format
                    Map<String, Object> output = new HashMap<>();
                    output.put("function", functionSignature);
    
                    // Get the input names and create the "args" field
                    Map<String, Object> args = new LinkedHashMap<>();
                    List<Map<String, Object>> inputs = (List<Map<String, Object>>) functionDefinition.get("inputs");
                    for (int i = 0; i < inputs.size(); i++) {
                        String name = (String) inputs.get(i).get("name");
                        if (name == null || name.isEmpty()) {
                            name = "param" + i; // Assign a default name if not provided
                        }
                        Object value = extractValueNamed(decodedInput.get(i), inputs.get(i), abiList);
                        args.put(name, value);
                    }
    
                    output.put("args", args);
                    return output;
                }
            }
        }
    
        throw new IllegalArgumentException("No matching function for selector: " + methodSelector);
    }

    // Helper method to extract value from Type, handling nested structures
    private static Object extractValue(Type type) {
        if (type instanceof DynamicArray) {
            List<Object> values = new ArrayList<>();
            for (Object elem : ((DynamicArray<?>) type).getValue()) {
                values.add(extractValue((Type) elem));
            }
            return values;
        } else if (type instanceof StaticArray) {
            List<Object> values = new ArrayList<>();
            for (Object elem : ((StaticArray<?>) type).getValue()) {
                values.add(extractValue((Type) elem));
            }
            return values;
        } else if (type instanceof DynamicStruct) {
            List<Type> components = ((DynamicStruct) type).getValue();
            List<Object> values = new ArrayList<>();
            for (Type component : components) {
                values.add(extractValue(component));
            }
            return values;
        } else if (type instanceof StaticStruct) {
            List<Type> components = ((StaticStruct) type).getValue();
            List<Object> values = new ArrayList<>();
            for (Type component : components) {
                values.add(extractValue(component));
            }
            return values;
        } else if (type instanceof Address) {
            return ((Address) type).getValue();
        } else if (type instanceof Bytes || type instanceof DynamicBytes) {
            return Numeric.toHexString(((BytesType) type).getValue());
        } else {
            return type.getValue();
        }
    }

    /**
     * Like {@link #extractValue(Type)} but uses the parameter's ABI definition to
     * render structs/tuples as ordered name -> value maps. Arrays recurse on their
     * element definition; leaf values delegate to {@link #extractValue(Type)}.
     * Tuples whose components are unnamed (e.g. synthetic 4byte ABIs) stay as
     * positional lists.
     */
    private static Object extractValueNamed(Type type, Map<String, Object> definition, List<Map<String, Object>> abiList) {
        if (definition == null) {
            return extractValue(type);
        }

        // NOTE: order matters. web3j's StaticStruct/DynamicStruct extend
        // StaticArray/DynamicArray, so structs must be matched before arrays.
        if (type instanceof DynamicStruct || type instanceof StaticStruct) {
            List<Type> components = (type instanceof DynamicStruct)
                    ? ((DynamicStruct) type).getValue()
                    : ((StaticStruct) type).getValue();

            List<Map<String, Object>> componentDefs;
            try {
                componentDefs = getStructComponents(definition, abiList);
            } catch (ClassNotFoundException e) {
                componentDefs = null;
            }

            if (componentDefs == null || componentDefs.size() != components.size() || !allComponentsNamed(componentDefs)) {
                List<Object> values = new ArrayList<>();
                for (Type component : components) {
                    values.add(extractValue(component));
                }
                return values;
            }

            Map<String, Object> named = new LinkedHashMap<>();
            for (int i = 0; i < components.size(); i++) {
                named.put((String) componentDefs.get(i).get("name"),
                        extractValueNamed(components.get(i), componentDefs.get(i), abiList));
            }
            return named;
        }

        if (type instanceof DynamicArray || type instanceof StaticArray) {
            Map<String, Object> elementDefinition = arrayElementDefinition(definition);
            List<?> elements = (type instanceof DynamicArray)
                    ? ((DynamicArray<?>) type).getValue()
                    : ((StaticArray<?>) type).getValue();
            List<Object> values = new ArrayList<>();
            for (Object elem : elements) {
                values.add(extractValueNamed((Type) elem, elementDefinition, abiList));
            }
            return values;
        }

        return extractValue(type);
    }

    private static boolean allComponentsNamed(List<Map<String, Object>> componentDefs) {
        for (Map<String, Object> def : componentDefs) {
            Object name = def.get("name");
            if (!(name instanceof String) || ((String) name).isEmpty()) {
                return false;
            }
        }
        return true;
    }

    private static Map<String, Object> arrayElementDefinition(Map<String, Object> definition) {
        String solidityType = normalizeSolidityType((String) definition.get("type"));
        String baseType;
        if (solidityType.endsWith("[]")) {
            baseType = solidityType.substring(0, solidityType.length() - 2);
        } else if (solidityType.matches("^.*\\[\\d+\\]$")) {
            baseType = solidityType.substring(0, solidityType.indexOf('['));
        } else {
            baseType = solidityType;
        }
        Map<String, Object> elementDefinition = cloneParameterDefinition(definition);
        elementDefinition.put("type", baseType);
        return elementDefinition;
    }

    // Method to build function signature (e.g., myFunction(address,uint256))
    // Delegates to AbiSelectorBuilder so the canonical-signature/selector logic
    // lives in one place (shared with passive ABI detection).
    private static String buildMethodSignature(Map<String, Object> functionDefinition) {
        return AbiSelectorBuilder.canonicalSignature(functionDefinition);
    }

    // Method to build the method selector (first 4 bytes of the function signature hash)
    private static String buildMethodSelector(Map<String, Object> functionDefinition) {
        return AbiSelectorBuilder.selectorFor(functionDefinition);
    }

    // Method to get input parameter types from ABI
    private static List<org.web3j.abi.TypeReference<?>> getInputParameterTypes(Map<String, Object> functionDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        List<org.web3j.abi.TypeReference<?>> parameterTypes = new ArrayList<>();
        List<Map<String, Object>> inputs = (List<Map<String, Object>>) functionDefinition.get("inputs");

        for (Map<String, Object> input : inputs) {
            org.web3j.abi.TypeReference<?> typeReference = getTypeReference(input, abiList);
            parameterTypes.add(typeReference);
        }

        return parameterTypes;
    }

    // Convert Solidity types to TypeReference instances
    private static org.web3j.abi.TypeReference<?> getTypeReference(Map<String, Object> parameterDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));

        if (solidityType.endsWith("[]") || solidityType.matches("^.*\\[\\d+\\]$")) {
            return getArrayTypeReference(parameterDefinition, abiList);
        } else if (solidityType.startsWith(TYPE_TUPLE) || isStruct(solidityType, abiList)) {
            return getStructTypeReference(parameterDefinition, abiList);
        }

        if (solidityType.startsWith("bytes") && !solidityType.equals("bytes")) {
            int size = Integer.parseInt(solidityType.substring(5));
            return getBytesTypeReference(size);
        }

        return org.web3j.abi.TypeReference.makeTypeReference(solidityType);
    }

    // Updated method to handle array type references
    private static org.web3j.abi.TypeReference<?> getArrayTypeReference(Map<String, Object> parameterDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        String baseType;
        int arraySize = -1; // -1 indicates dynamic array

        if (solidityType.endsWith("[]")) {
            // Dynamic array
            baseType = solidityType.substring(0, solidityType.length() - 2);
        } else if (solidityType.matches("^.*\\[\\d+\\]$")) {
            // Fixed-size array
            int startIndex = solidityType.indexOf('[');
            int endIndex = solidityType.indexOf(']');
            baseType = solidityType.substring(0, startIndex);
            arraySize = Integer.parseInt(solidityType.substring(startIndex + 1, endIndex));
        } else {
            throw new ClassNotFoundException("Invalid array type: " + solidityType);
        }

        Map<String, Object> baseTypeDefinition = cloneParameterDefinition(parameterDefinition);
        baseTypeDefinition.put("type", baseType);

        final org.web3j.abi.TypeReference<?> baseTypeReference = getTypeReference(baseTypeDefinition, abiList);

        if (arraySize == -1) {
            return new org.web3j.abi.TypeReference<DynamicArray<?>>() {
                @Override
                public java.lang.reflect.Type getType() {
                    return new ParameterizedTypeImpl(DynamicArray.class, baseTypeReference.getType());
                }

                // web3j's TypeDecoder reads getSubTypeReference().getInnerTypes()
                // to decode struct elements without a generated class. Expose the
                // element reference so arrays of tuples decode via inner types.
                @Override
                public org.web3j.abi.TypeReference getSubTypeReference() {
                    return baseTypeReference;
                }
            };
        } else {
            Class<? extends StaticArray> arrayClass = (Class<? extends StaticArray>) loadGeneratedClass(
                    "org.web3j.abi.datatypes.generated.StaticArray",
                    arraySize,
                    "StaticArray" + arraySize + " not supported."
            );

            return new StaticArrayTypeReference<StaticArray<?>>(arraySize) {
                @Override
                public java.lang.reflect.Type getType() {
                    return new ParameterizedTypeImpl(arrayClass, baseTypeReference.getType());
                }

                @Override
                public org.web3j.abi.TypeReference getSubTypeReference() {
                    return baseTypeReference;
                }
            };
        }
    }

    // Helper class to create a ParameterizedType
    public static class ParameterizedTypeImpl implements java.lang.reflect.ParameterizedType {
        private final java.lang.reflect.Type rawType;
        private final java.lang.reflect.Type[] typeArguments;

        public ParameterizedTypeImpl(java.lang.reflect.Type rawType, java.lang.reflect.Type... typeArguments) {
            this.rawType = rawType;
            this.typeArguments = typeArguments;
        }

        @Override
        public java.lang.reflect.Type[] getActualTypeArguments() {
            return typeArguments;
        }

        @Override
        public java.lang.reflect.Type getRawType() {
            return rawType;
        }

        @Override
        public java.lang.reflect.Type getOwnerType() {
            return null;
        }

        @Override
        public String getTypeName() {
            StringBuilder builder = new StringBuilder(((Class<?>) rawType).getName());
            if (typeArguments.length > 0) {
                builder.append("<");
                for (int i = 0; i < typeArguments.length; i++) {
                    builder.append(typeArguments[i].getTypeName());
                    if (i < typeArguments.length - 1) {
                        builder.append(", ");
                    }
                }
                builder.append(">");
            }
            return builder.toString();
        }
    }

    // Utility method to get fixed-size bytes type reference
    private static org.web3j.abi.TypeReference<?> getBytesTypeReference(int size) throws ClassNotFoundException {
        if (size < 1 || size > 32) {
            throw new ClassNotFoundException("Bytes" + size + " not supported.");
        }

        Class<?> bytesClass = loadGeneratedClass("org.web3j.abi.datatypes.generated.Bytes", size, "Bytes" + size + " not supported.");

        return new org.web3j.abi.TypeReference<Type>() {
            @Override
            public java.lang.reflect.Type getType() {
                return bytesClass;
            }
        };
    }

    // Utility method to check if a type is a struct by looking it up in the ABI list
    private static boolean isStruct(String solidityType, List<Map<String, Object>> abiList) {
        for (Map<String, Object> abiDefinition : abiList) {
            if ("struct".equals(abiDefinition.get("type")) && solidityType.equals(abiDefinition.get("name"))) {
                return true;
            }
        }
        return false;
    }

    // encode input data
    public static String encodeInput(String abiJson, String functionSignature, Map<String, Object> args) throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        List<Map<String, Object>> abiList = objectMapper.readValue(abiJson, new TypeReference<List<Map<String, Object>>>() {});
    
        // Find the function definition in the ABI by matching the function signature
        Map<String, Object> functionDefinition = null;
        for (Map<String, Object> abiEntry : abiList) {
            if ("function".equals(abiEntry.get("type"))) {
                // Build the function signature for this function
                String abiFunctionSignature = buildMethodSignature(abiEntry);
                if (functionSignature.equals(abiFunctionSignature)) {
                    functionDefinition = abiEntry;
                    break;
                }
            }
        }
    
        if (functionDefinition == null) {
            throw new IllegalArgumentException("Function " + functionSignature + " not found in ABI.");
        }
    
        // Build input parameters
        List<Type> inputParameters = buildInputParameters(functionDefinition, args, abiList);
    
        // Extract function name from the function signature
        String functionName = functionSignature.substring(0, functionSignature.indexOf('('));
    
        // Create the Function object
        Function function = new Function(functionName, inputParameters, Collections.emptyList());
    
        // Encode the function call
        String encodedFunction = FunctionEncoder.encode(function);
    
        return encodedFunction;
    }

    // Helper method to build input parameters
    private static List<Type> buildInputParameters(Map<String, Object> functionDefinition, Map<String, Object> args, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        List<Type> inputParameters = new ArrayList<>();
        List<Map<String, Object>> inputs = (List<Map<String, Object>>) functionDefinition.get("inputs");

        for (Map<String, Object> input : inputs) {
            String name = (String) input.get("name");
            Object value = args.get(name);

            if (value == null) {
                throw new IllegalArgumentException("Argument " + name + " is missing.");
            }

            Type parameter = getTypeInstance(input, value, abiList);
            inputParameters.add(parameter);
        }

        return inputParameters;
    }

    // Convert Solidity types to Type instances
    private static Type getTypeInstance(Map<String, Object> parameterDefinition, Object value, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        if (solidityType.endsWith("[]") || solidityType.matches("^.*\\[\\d+\\]$")) {
            // Handle arrays
            return getArrayTypeInstance(parameterDefinition, value, abiList);
        } else if (solidityType.startsWith(TYPE_TUPLE) || isStruct(solidityType, abiList)) {
            // Handle structs
            Map<String, Object> valueMap = (Map<String, Object>) value;
            return getStructTypeInstance(parameterDefinition, valueMap, abiList);
        } else if ("address".equals(solidityType)) {
            return new Address((String) value);
        } else if ("bool".equals(solidityType)) {
            return new Bool(Boolean.parseBoolean(value.toString()));
        } else if (solidityType.startsWith("uint")) {
            int size = Integer.parseInt(solidityType.substring(4));
            return getUintTypeInstance(size, value);
        } else if (solidityType.startsWith("int")) {
            int size = Integer.parseInt(solidityType.substring(3));
            return getIntTypeInstance(size, value);
        } else if ("string".equals(solidityType)) {
            return new Utf8String((String) value);
        } else if ("bytes".equals(solidityType)) {
            return new DynamicBytes(Numeric.hexStringToByteArray((String) value));
        } else if (solidityType.startsWith("bytes") && !"bytes".equals(solidityType)) {
            int size = Integer.parseInt(solidityType.substring(5));
            return getBytesTypeInstance(size, value);
        } else {
            throw new ClassNotFoundException("Type not supported: " + solidityType);
        }
    }

    // Utility method to handle array type instances
    private static Type<?> getArrayTypeInstance(Map<String, Object> parameterDefinition, Object value, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        String baseType;
        int arraySize = -1; // -1 indicates dynamic array

        if (solidityType.endsWith("[]")) {
            // Dynamic array
            baseType = solidityType.substring(0, solidityType.length() - 2);
        } else if (solidityType.matches("^.*\\[\\d+\\]$")) {
            // Fixed-size array
            int startIndex = solidityType.indexOf('[');
            int endIndex = solidityType.indexOf(']');
            baseType = solidityType.substring(0, startIndex);
            arraySize = Integer.parseInt(solidityType.substring(startIndex + 1, endIndex));
        } else {
            throw new ClassNotFoundException("Invalid array type: " + solidityType);
        }

        List<?> valueList = (List<?>) value;
        List<Type> arrayElements = new ArrayList<>();

        Map<String, Object> baseTypeDefinition = cloneParameterDefinition(parameterDefinition);
        baseTypeDefinition.put("type", baseType);

        for (Object elem : valueList) {
            arrayElements.add(getTypeInstance(baseTypeDefinition, elem, abiList));
        }

        if (arraySize == -1) {
            // Dynamic array. web3j deprecated DynamicArray(List) (it can't infer the
            // element type from an empty list); pass the element class explicitly.
            // Non-empty: the runtime element class (what the old ctor inferred).
            // Empty: derive it from the ABI so empty arrays still encode.
            @SuppressWarnings("unchecked")
            Class<Type> elementClass = arrayElements.isEmpty()
                    ? (Class<Type>) getTypeReference(baseTypeDefinition, abiList).getClassType()
                    : (Class<Type>) arrayElements.get(0).getClass();
            return new DynamicArray<>(elementClass, arrayElements);
        } else {
            if (valueList.size() != arraySize) {
                throw new IllegalArgumentException("Expected array of size " + arraySize + " for type " + solidityType);
            }
            // Get the correct StaticArrayN class
            Class<?> staticArrayClass;
            try {
                staticArrayClass = loadGeneratedClass("org.web3j.abi.datatypes.generated.StaticArray", arraySize, "StaticArray" + arraySize + " not supported.");
            } catch (ClassNotFoundException e) {
                throw new RuntimeException("StaticArray" + arraySize + " not supported.", e);
            }

            // Get the constructor that accepts a List of Type
            Constructor<?> constructor;
            try {
                constructor = staticArrayClass.getConstructor(List.class);

                Type staticArrayInstance = (Type) constructor.newInstance(arrayElements);

                return staticArrayInstance;
            } catch (NoSuchMethodException | InstantiationException | IllegalAccessException | IllegalArgumentException
            | InvocationTargetException | SecurityException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
                throw new RuntimeException("StaticArray" + arraySize + " not supported.");
            }
            
            //return new StaticArray<Type>(arraySize, arrayElements);
        }
    }

    // Utility method to get Uint type instance
    private static Type getUintTypeInstance(int size, Object value) throws ClassNotFoundException {
        BigInteger bigIntValue = new BigInteger(value.toString());
        switch (size) {
            case 8:
                return new Uint8(bigIntValue);
            case 16:
                return new Uint16(bigIntValue);
            case 32:
                return new Uint32(bigIntValue);
            case 64:
                return new Uint64(bigIntValue);
            case 128:
                return new Uint128(bigIntValue);
            case 256:
                return new Uint256(bigIntValue);
            default:
                throw new ClassNotFoundException("Uint" + size + " not supported.");
        }
    }

    // Utility method to get Int type instance
    private static Type getIntTypeInstance(int size, Object value) throws ClassNotFoundException {
        BigInteger bigIntValue = new BigInteger(value.toString());
        switch (size) {
            case 8:
                return new Int8(bigIntValue);
            case 16:
                return new Int16(bigIntValue);
            case 32:
                return new Int32(bigIntValue);
            case 64:
                return new Int64(bigIntValue);
            case 128:
                return new Int128(bigIntValue);
            case 256:
                return new Int256(bigIntValue);
            default:
                throw new ClassNotFoundException("Int" + size + " not supported.");
        }
    }

    // Utility method to get fixed-size bytes type instance
    private static Type getBytesTypeInstance(int size, Object value) throws ClassNotFoundException {
        if (size < 1 || size > 32) {
            throw new ClassNotFoundException("Bytes" + size + " not supported.");
        }

        byte[] bytesValue = Numeric.hexStringToByteArray((String) value);
        try {
            Class<?> bytesClass = loadGeneratedClass("org.web3j.abi.datatypes.generated.Bytes", size, "Bytes" + size + " not supported.");
            Constructor<?> constructor = bytesClass.getConstructor(byte[].class);
            return (Type) constructor.newInstance(bytesValue);
        } catch (NoSuchMethodException | InstantiationException | IllegalAccessException | InvocationTargetException e) {
            throw new RuntimeException("Bytes" + size + " not supported.", e);
        }
    }

    // Utility method to handle struct type instances
    private static Type getStructTypeInstance(Map<String, Object> parameterDefinition, Map<String, Object> value, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        List<Map<String, Object>> components = getStructComponents(parameterDefinition, abiList);
        List<Type> structFields = new ArrayList<>();
        for (Map<String, Object> component : components) {
            String fieldName = (String) component.get("name");
            Object fieldValue = value.get(fieldName);
            if (fieldValue == null) {
                throw new IllegalArgumentException("Field " + fieldName + " is missing in struct " + solidityType);
            }
            structFields.add(getTypeInstance(component, fieldValue, abiList));
        }
        // web3j's base struct types compute their canonical signature recursively
        // from the component instances, so no generated subclass is needed to
        // encode (even for nested tuples). Static vs dynamic must still match the
        // ABI so the encoder applies the correct layout.
        if (isDynamicStruct(components, abiList)) {
            return new DynamicStruct(structFields);
        }
        return new StaticStruct(structFields);
    }

    /**
     * Decodes the output data of a function call given the ABI JSON, function signature, and output data.
     *
     * @param abiJson           The ABI JSON string.
     * @param functionSignature The function signature (e.g., "transfer(address,uint256)").
     * @param outputData        The output data hex string (e.g., "0x...").
     * @return A map containing the function name and decoded output values.
     * @throws Exception If decoding fails.
     */
    public static Map<String, Object> decodeOutput(String abiJson, String functionSignature, String outputData) throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        List<Map<String, Object>> abiList = objectMapper.readValue(abiJson, new TypeReference<List<Map<String, Object>>>() {});

        // Find the function definition in the ABI by matching the function signature
        Map<String, Object> functionDefinition = null;
        for (Map<String, Object> abiEntry : abiList) {
            if ("function".equals(abiEntry.get("type"))) {
                // Build the function signature for this function
                String abiFunctionSignature = buildMethodSignature(abiEntry);
                if (functionSignature.equals(abiFunctionSignature)) {
                    functionDefinition = abiEntry;
                    break;
                }
            }
        }

        if (functionDefinition == null) {
            throw new IllegalArgumentException("Function " + functionSignature + " not found in ABI.");
        }

        // Get output parameter types from ABI
        List<org.web3j.abi.TypeReference<?>> outputParameters = getOutputParameterTypes(functionDefinition, abiList);

        // Cast outputParameters to List<TypeReference<Type>>
        @SuppressWarnings("unchecked")
        List<org.web3j.abi.TypeReference<Type>> typeReferences = (List<org.web3j.abi.TypeReference<Type>>)(List<?>) outputParameters;

        // Decode the output data
        List<Type> decodedOutput = FunctionReturnDecoder.decode(outputData, typeReferences);

        // Create the output in the desired format
        Map<String, Object> output = new LinkedHashMap<>();

        // Get the output parameter names and create the "output" field
        Map<String, Object> outputValues = new LinkedHashMap<>();
        List<Map<String, Object>> outputs = (List<Map<String, Object>>) functionDefinition.get("outputs");
        for (int i = 0; i < outputs.size(); i++) {
            String name = (String) outputs.get(i).get("name");
            if (name == null || name.isEmpty()) {
                name = "output" + i; // Assign a default name if not provided
            }
            Object value = extractValueNamed(decodedOutput.get(i), outputs.get(i), abiList);
            outputValues.put(name, value);
        }

        output.put("function", functionSignature);
        output.put("output", outputValues);
        return output;
    }

    // Method to get output parameter types from ABI
    private static List<org.web3j.abi.TypeReference<?>> getOutputParameterTypes(Map<String, Object> functionDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        List<org.web3j.abi.TypeReference<?>> parameterTypes = new ArrayList<>();
        List<Map<String, Object>> outputs = (List<Map<String, Object>>) functionDefinition.get("outputs");

        for (Map<String, Object> output : outputs) {
            org.web3j.abi.TypeReference<?> typeReference = getTypeReference(output, abiList);
            parameterTypes.add(typeReference);
        }

        return parameterTypes;
    }

    private static void validateMethodInputData(String inputData) {
        if (inputData == null || !inputData.startsWith("0x") || inputData.length() < 10) {
            throw new IllegalArgumentException("Input data must start with 0x and include a 4-byte selector.");
        }
    }

    private static String normalizeSolidityType(String solidityType) {
        if ("uint".equals(solidityType)) {
            return "uint256";
        }
        if ("int".equals(solidityType)) {
            return "int256";
        }
        return solidityType;
    }

    private static List<Map<String, Object>> getStructComponents(Map<String, Object> parameterDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        List<Map<String, Object>> components = (List<Map<String, Object>>) parameterDefinition.get("components");
        if (components != null && !components.isEmpty()) {
            return components;
        }

        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        for (Map<String, Object> abiDefinition : abiList) {
            if ("struct".equals(abiDefinition.get("type")) && solidityType.equals(abiDefinition.get("name"))) {
                return (List<Map<String, Object>>) abiDefinition.get("components");
            }
        }

        throw new ClassNotFoundException("Struct " + solidityType + " not found.");
    }

    /**
     * Builds a runtime {@link org.web3j.abi.TypeReference} for a struct/tuple from
     * its ABI component definitions, using web3j's native inner-type decoding
     * (TypeReference + TypeDecoder support added in 4.12.1). The returned reference
     * carries the component TypeReferences via {@code getInnerTypes()}; web3j's
     * TypeDecoder reads those to decode the struct without a generated wrapper
     * class. The static-vs-dynamic base type selects the correct ABI layout rules.
     */
    private static org.web3j.abi.TypeReference<?> getStructTypeReference(
            Map<String, Object> parameterDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        List<Map<String, Object>> components = getStructComponents(parameterDefinition, abiList);
        List<org.web3j.abi.TypeReference<?>> innerTypes = new ArrayList<>(components.size());
        for (Map<String, Object> component : components) {
            innerTypes.add(getTypeReference(component, abiList));
        }

        if (isDynamicStruct(components, abiList)) {
            return new org.web3j.abi.TypeReference<DynamicStruct>(false, innerTypes) {};
        }
        return new org.web3j.abi.TypeReference<StaticStruct>(false, innerTypes) {};
    }

    private static boolean isDynamicStruct(List<Map<String, Object>> components, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        for (Map<String, Object> component : components) {
            if (isDynamicType(component, abiList)) {
                return true;
            }
        }
        return false;
    }

    private static boolean isDynamicType(Map<String, Object> parameterDefinition, List<Map<String, Object>> abiList) throws ClassNotFoundException {
        String solidityType = normalizeSolidityType((String) parameterDefinition.get("type"));
        if ("bytes".equals(solidityType) || "string".equals(solidityType)) {
            return true;
        }
        if (solidityType.endsWith("[]")) {
            return true;
        }
        if (solidityType.matches("^.*\\[\\d+\\]$")) {
            String baseType = solidityType.substring(0, solidityType.indexOf('['));
            Map<String, Object> baseTypeDefinition = cloneParameterDefinition(parameterDefinition);
            baseTypeDefinition.put("type", baseType);
            return isDynamicType(baseTypeDefinition, abiList);
        }
        if (solidityType.startsWith(TYPE_TUPLE) || isStruct(solidityType, abiList)) {
            return isDynamicStruct(getStructComponents(parameterDefinition, abiList), abiList);
        }
        return false;
    }

    private static Map<String, Object> cloneParameterDefinition(Map<String, Object> parameterDefinition) {
        Map<String, Object> clone = new HashMap<>(parameterDefinition);
        if (parameterDefinition.containsKey("components")) {
            clone.put("components", parameterDefinition.get("components"));
        }
        return clone;
    }

    private static Class<?> loadGeneratedClass(String prefix, int suffix, String errorMessage) throws ClassNotFoundException {
        try {
            return Class.forName(prefix + suffix);
        } catch (ClassNotFoundException e) {
            throw new ClassNotFoundException(errorMessage, e);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2 && args.length != 3) {
            System.out.println("Usage for decoding: ABIInputDecoder <ABI file path> <input data hex string>");
            System.out.println("Usage for encoding: ABIInputDecoder <ABI file path> <function name> <args JSON>");
            return;
        }

        String abiFilePath = args[0];
        String abiJson = new String(Files.readAllBytes(Paths.get(abiFilePath)));

        if (args.length == 2) {
            String inputData = args[1];

            // Decode the input data
            Map<String, Object> decodedData = decodeInput(abiJson, inputData);

            // Convert the result to JSON and print
            ObjectMapper mapper = new ObjectMapper();
            String jsonOutput = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(decodedData);
            System.out.println(jsonOutput);
        } else if (args.length == 3) {
            String functionName = args[1];
            String argsJson = args[2];

            // Parse the args JSON
            ObjectMapper mapper = new ObjectMapper();
            Map<String, Object> argsMap = mapper.readValue(argsJson, new TypeReference<Map<String, Object>>() {});

            // Encode the input data
            String encodedData = encodeInput(abiJson, functionName, argsMap);

            // Print the encoded data
            System.out.println(encodedData);
        }
    }
}
