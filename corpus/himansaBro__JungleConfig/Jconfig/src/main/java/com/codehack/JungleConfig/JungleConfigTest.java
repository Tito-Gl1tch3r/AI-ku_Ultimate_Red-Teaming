package com.codehack.JungleConfig;

import com.codehack.JungleConfig.Core.Adapters.*;
import com.fasterxml.jackson.core.type.TypeReference;
import java.io.File;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;

/**
 * Professional Test Suite for JungleConfig Framework.
 * Validates all core features, type adapters, and configuration modes.
 */
public class JungleConfigTest {

    private static final String RESET = "\u001B[0m";
    private static final String GREEN = "\u001B[32m";
    private static final String RED = "\u001B[31m";
    private static final String CYAN = "\u001B[36m";
    private static final String YELLOW = "\u001B[33m";

    static class User {
        public String name;
        public int age;

        public User() {
        }

        public User(String name, int age) {
            this.name = name;
            this.age = age;
        }

        @Override
        public String toString() {
            return name + " (" + age + ")";
        }

        @Override
        public boolean equals(Object o) {
            if (this == o)
                return true;
            if (o == null || getClass() != o.getClass())
                return false;
            User user = (User) o;
            return age == user.age && Objects.equals(name, user.name);
        }
    }

    public static void main(String[] args) {
        System.out.println(CYAN + "========================================" + RESET);
        System.out.println(CYAN + "   JungleConfig Professional Test Suite  " + RESET);
        System.out.println(CYAN + "========================================" + RESET);

        TestRunner runner = new TestRunner();

        runner.testGroup("Standard Configuration (File)", () -> {
            File file = new File("test_standard.conf");
            if (file.exists())
                file.delete();
            JungleConfig config = new JungleConfig(file);
            testCoreFeatures(config);
            // file.delete();
        });

        runner.testGroup("Encrypted Configuration", () -> {
            File file = new File("test_encrypted.conf");
            if (file.exists())
                file.delete();
            JungleConfig config = JungleConfig.EncryptedConfig(file, "secure_password_123");
            testCoreFeatures(config);
            // file.delete();
        });

        runner.testGroup("InMemory Configuration", () -> {
            JungleConfig config = JungleConfig.InMemoryConfig();
            testCoreFeatures(config);
        });

        runner.testGroup("FlatJson Configuration", () -> {
            JungleConfig config = JungleConfig.FlatJsonConfig();
            testCoreFeatures(config);
        });

        runner.testGroup("Transaction Logic (Commit/Rollback)", () -> {
            JungleConfig config = JungleConfig.InMemoryConfig();

            // Commit Test
            config.BeginTransaction();
            config.Set("tx.commit", "success");
            config.Commit();
            assert "success".equals(config.get("tx.commit", String.class));

            // Rollback Test
            config.BeginTransaction();
            config.Set("tx.rollback", "should_fail");
            config.Rollback();
            assert !config.Get("tx.rollback", String.class).isPresent();
        });

        runner.printSummary();

        if (runner.hasFailures()) {
            System.exit(1);
        }
    }

    private static void testCoreFeatures(JungleConfig config) {
        // 1. Basic Primitives
        config.Set("key.str", "Hello World");
        config.Set("key.bool", true);
        config.Set("key.int", 42);
        assert "Hello World".equals(config.get("key.str", String.class));
        assert config.get("key.bool", Boolean.class);
        assert 42 == config.get("key.int", Integer.class);

        // 2. New Numeric Adapters
        config.Set("key.long", Long.MAX_VALUE);
        config.Set("key.double", 3.14159);
        config.Set("key.float", 1.23f);
        assert Long.MAX_VALUE == config.get("key.long", Long.class);
        assert 3.14159 == config.get("key.double", Double.class);
        assert 1.23f == config.get("key.float", Float.class);

        // 3. Utility Types
        UUID uuid = UUID.randomUUID();
        config.Set("key.uuid", uuid);
        assert uuid.equals(config.get("key.uuid", UUID.class));

        // 4. Java Time
        LocalDate date = LocalDate.of(2024, 2, 29);
        LocalDateTime dateTime = LocalDateTime.of(2024, 2, 29, 12, 0, 0);
        LocalTime time = LocalTime.of(12, 34, 56);
        config.Set("key.date", date);
        config.Set("key.datetime", dateTime);
        config.Set("key.time", time);
        assert date.equals(config.get("key.date", LocalDate.class));
        assert dateTime.equals(config.get("key.datetime", LocalDateTime.class));
        assert time.equals(config.get("key.time", LocalTime.class));

        // 5. Complex Types (POJO & Collections)
        User user = new User("Himansa", 19);
        config.SetPOJO("key.pojo", user);
        assert user.equals(config.get("key.pojo", User.class));

        List<String> list = Arrays.asList("A", "B", "C");
        config.Set("key.list", list);
        List<String> resultList = config.getCollection("key.list", new TypeReference<List<String>>() {
        });
        assert list.equals(resultList);

        // 6. Null Handling (Verify Fix)
        config.Set("key.null", null);
        assert "null".equals(config.getTypeSimpleName("key.null"));
    }

    static class TestRunner {
        private int passedCount = 0;
        private int failedCount = 0;
        private final List<String> failures = new ArrayList<>();

        public void testGroup(String name, Runnable test) {
            System.out.print(YELLOW + "Testing " + name + "... " + RESET);
            try {
                test.run();
                System.out.println(GREEN + "✅ PASSED" + RESET);
                passedCount++;
            } catch (Throwable e) {
                System.out.println(RED + "❌ FAILED" + RESET);
                failedCount++;
                failures.add(name + ": " + e.getMessage());
                e.printStackTrace();
            }
        }

        public void printSummary() {
            System.out.println(CYAN + "\nTest Summary:" + RESET);
            System.out.println(GREEN + "  Passed: " + passedCount + RESET);
            System.out.println(RED + "  Failed: " + failedCount + RESET);
            if (!failures.isEmpty()) {
                System.out.println(RED + "Failures:" + RESET);
                for (String f : failures)
                    System.out.println("  - " + f);
            }
        }

        public boolean hasFailures() {
            return failedCount > 0;
        }
    }
}
