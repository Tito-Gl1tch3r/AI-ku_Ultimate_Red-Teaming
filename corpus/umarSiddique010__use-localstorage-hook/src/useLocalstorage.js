import { useCallback, useEffect, useState } from "react";

function useLocalstorage(storeName, initialData) {
  if (!storeName || initialData === undefined) {
    throw new Error("useLocalstorage: storeName and initialData are required.");
  }
  const key = storeName?.toString?.();

  const [getStore, setGetStore] = useState(() => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialData;
    } catch (err) {
      console.error(`Error reading localStorage key "${key}":`, err);
      localStorage.removeItem(key);
      return initialData;
    }
  });

  const setStore = useCallback(
    (data) => {
      try {
        localStorage.setItem(key, JSON.stringify(data));
        setGetStore(data);
      } catch (err) {
        throw new Error(`useLocalstorage: Failed to set item: ${err.message}`);
      }
    },
    [key]
  );


  const removeStore = useCallback(() => {
    try {
      localStorage.removeItem(key);
      setGetStore(null);
    } catch (err) {
      throw new Error(`Error while removing localstorage item: ${err.message}`);
    }
  }, [key]);

  const clearAllStore = useCallback(() => {
    try {
      localStorage.clear();
      setGetStore(null);
    } catch (err) {
      console.error(`Error clearing localstorage: ${err.message}`);
    }
  }, []);

  useEffect(() => {
    const handleStoreChange = (e) => {
      if (e.key === key) {
        try {
          if (e.newValue === null) {
            setGetStore(null);
          } else {
            setGetStore(JSON.parse(e.newValue));
          }
        } catch (err) {
          console.error(`Error parsing storage event for key "${key}" : ${err}`)
          setGetStore(null);
        }
      }
    };

    window.addEventListener('storage', handleStoreChange)

    return () => window.removeEventListener('storage', handleStoreChange)
  }, [key]);

  useEffect(() => {
    try {
      const existing = localStorage.getItem(key);

      if (existing === null) {
        setStore(initialData);
      }
    } catch (err) {
      console.error(`Error initializing localStorage key "${key}":`, err);

    }
  }, [key, initialData, setStore]);

  return {
    setStore,
    getStore,
    removeStore,
    clearAllStore,
  };
}

export default useLocalstorage;
