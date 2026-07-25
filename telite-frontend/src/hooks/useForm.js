import { useState, useCallback } from 'react';

/**
 * Custom hook for form state management
 * @param {object} initialValues - Initial form values
 * @param {object} validationSchema - Optional validation schema
 * @returns {object} - Form state and handlers
 */
export function useForm(initialValues = {}, validationSchema = null) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const setValue = useCallback((name, value) => {
    setValues(prev => ({ ...prev, [name]: value }));
    
    // Clear error when value changes
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  }, [errors]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const finalValue = type === 'checkbox' ? checked : value;
    setValue(name, finalValue);
  }, [setValue]);

  const handleBlur = useCallback((e) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
    
    // Validate on blur if schema exists
    if (validationSchema && validationSchema[name]) {
      const error = validationSchema[name](values[name]);
      setErrors(prev => ({ ...prev, [name]: error }));
    }
  }, [validationSchema, values]);

  const setFieldValue = useCallback((name, value) => {
    setValue(name, value);
    setTouched(prev => ({ ...prev, [name]: true }));
  }, [setValue]);

  const setFieldError = useCallback((name, error) => {
    setErrors(prev => ({ ...prev, [name]: error }));
  }, []);

  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  const validate = useCallback(() => {
    if (!validationSchema) return true;
    
    const newErrors = {};
    let isValid = true;
    
    Object.keys(validationSchema).forEach((key) => {
      const error = validationSchema[key](values[key]);
      if (error) {
        newErrors[key] = error;
        isValid = false;
      }
    });
    
    setErrors(newErrors);
    setTouched(Object.keys(validationSchema).reduce((acc, key) => ({ ...acc, [key]: true }), {}));
    
    return isValid;
  }, [validationSchema, values]);

  const isValid = Object.keys(errors).every(key => !errors[key]);

  return {
    values,
    errors,
    touched,
    isValid,
    handleChange,
    handleBlur,
    setFieldValue,
    setFieldError,
    resetForm,
    validate,
    setValues
  };
}
