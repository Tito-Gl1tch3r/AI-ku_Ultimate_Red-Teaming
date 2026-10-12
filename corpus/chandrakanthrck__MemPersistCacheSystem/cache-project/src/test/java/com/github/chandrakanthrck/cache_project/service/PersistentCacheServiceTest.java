//package com.github.chandrakanthrck.cache_project.service;
//
//import com.github.chandrakanthrck.cache_project.model.CacheEntry;
//import com.github.chandrakanthrck.cache_project.repository.CacheRepository;
//import io.micrometer.core.instrument.Counter;
//import io.micrometer.core.instrument.MeterRegistry;
//import io.micrometer.core.instrument.Tags;
//import org.junit.jupiter.api.BeforeEach;
//import org.junit.jupiter.api.Test;
//import org.mockito.ArgumentCaptor;
//import org.mockito.InjectMocks;
//import org.mockito.Mock;
//import org.mockito.MockitoAnnotations;
//
//import java.util.Optional;
//
//import static org.junit.jupiter.api.Assertions.*;
//import static org.mockito.Mockito.*;
//
//class PersistentCacheServiceTest {
//
//    @Mock
//    private CacheRepository cacheRepository;
//
//    @Mock
//    private MeterRegistry meterRegistry;
//
//    @InjectMocks
//    private PersistentCacheService persistentCacheService;
//
//    private Counter counterMock;
//
//    @BeforeEach
//    void setUp() {
//        MockitoAnnotations.openMocks(this);
//        counterMock = mock(Counter.class);
//        when(meterRegistry.counter("cache.put", Tags.of("cache", "persistent"))).thenReturn(counterMock);
//        when(meterRegistry.counter("cache.hit", Tags.of("cache", "persistent"))).thenReturn(counterMock);
//        when(meterRegistry.counter("cache.miss", Tags.of("cache", "persistent"))).thenReturn(counterMock);
//        when(meterRegistry.counter("cache.remove", Tags.of("cache", "persistent"))).thenReturn(counterMock);
//        when(meterRegistry.counter("cache.clear", Tags.of("cache", "persistent"))).thenReturn(counterMock);
//    }
//
//    @Test
//    void testPut() {
//        String key = "key1";
//        String value = "value1";
//
//        persistentCacheService.put(key, value);
//
//        ArgumentCaptor<CacheEntry> captor = ArgumentCaptor.forClass(CacheEntry.class);
//        verify(cacheRepository).save(captor.capture());
//
//        CacheEntry capturedEntry = captor.getValue();
//
//        assertEquals(key, capturedEntry.getCacheKey(), "The key inside CacheEntry is incorrect");
//        assertEquals(value, capturedEntry.getCacheValue(), "The value inside CacheEntry is incorrect");
//        verify(counterMock).increment(); // Verify increment for put
//    }
//
//    @Test
//    void testGet() {
//        String key = "key1";
//        String value = "value1";
//        CacheEntry entry = new CacheEntry(key, value);
//
//        when(cacheRepository.findById(key)).thenReturn(Optional.of(entry));
//
//        String result = persistentCacheService.get(key);
//
//        assertEquals(value, result, "The returned value should match the expected value");
//        verify(counterMock).increment(); // Verify increment for hit
//    }
//
//    @Test
//    void testRemove() {
//        String key = "key1";
//
//        persistentCacheService.remove(key);
//
//        verify(cacheRepository).deleteById(key);
//        verify(counterMock).increment(); // Verify increment for remove
//    }
//
//    @Test
//    void testClear() {
//        persistentCacheService.clear();
//
//        verify(cacheRepository).deleteAll();
//        verify(counterMock).increment(); // Verify increment for clear
//    }
//
//    @Test
//    void testSize() {
//        when(cacheRepository.count()).thenReturn(5L);
//
//        int size = persistentCacheService.size();
//
//        assertEquals(5, size, "The size should match the expected value");
//        verify(meterRegistry).gauge("cache.size", Tags.of("cache", "persistent"), 5);
//    }
//}
