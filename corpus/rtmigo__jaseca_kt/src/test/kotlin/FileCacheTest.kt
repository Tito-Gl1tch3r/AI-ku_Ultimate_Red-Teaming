/*
 * SPDX-FileCopyrightText: (c) 2022 Artyom IG <github.com/rtmigo>
 * SPDX-License-Identifier: Apache-2.0
 */


@file:OptIn(Experimental::class)

import io.github.rtmigo.jaseca.*
import io.kotest.matchers.booleans.shouldBeTrue
import io.kotest.matchers.collections.shouldContain
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Disabled
import org.junit.jupiter.api.RepeatedTest
import org.junit.jupiter.api.Test
import java.util.UUID
import kotlin.concurrent.thread

class FileCacheTest {
    @Test
    fun storeIntegers() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("theCache")
            filecache<String, Int>(cacheDir).use { fileCache ->
                fileCache.put("A", 5)
                fileCache.put("B", 23)
            }

            filecache<String, Int>(cacheDir).use { fileCache ->
                fileCache["A"].shouldBe(5)
                fileCache["B"].shouldBe(23)
                fileCache["C"].shouldBeNull()
            }
        }
    }

    @Test
    fun storeDataclasses() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("theCache")
            filecache<Int, SampleClass>(cacheDir).use { fileCache ->
                fileCache.put(10, SampleClass("Masha", setOf("small", "pretty")))
                fileCache.put(12, SampleClass("Pasha", setOf("big", "handsome")))
            }

            filecache<Int, SampleClass>(cacheDir).use { fileCache ->
                fileCache[12]!!.name.shouldBe("Pasha")
                fileCache[12]!!.tags.shouldContain("handsome")
            }
        }
    }

    @Test
    fun getOrPut() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("getOrPut")
            filecache<String, Int>(cacheDir).use { fileCache ->
                fileCache.getOrPut("A") { 5 }.shouldBe(5)
                fileCache["A"].shouldBe(5)
            }
        }
    }

    @Test
    fun redingBeforeClosing() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("theCache")
            filecache<String, Int>(cacheDir).use { fileCache ->
                fileCache["A"].shouldBeNull()
                fileCache.put("A", 5)
                fileCache["A"].shouldBe(5)
            }
        }
    }

    @Test
    fun indexingOperators() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("theCache")
            filecache<String, Int>(cacheDir).use { fileCache ->
                fileCache["Answer"].shouldBeNull()
                fileCache["Answer"] = 42
                fileCache["Answer"].shouldBe(42)
            }
        }
    }

    @Disabled
    @RepeatedTest(25)
    fun randomFail() {
        withTempDir { tempDir ->
            val cacheDir = tempDir.resolve("cache")
            val t = thread {
                filecache<Int, String>(cacheDir).use { fileCache ->
                    fileCache[1] = "one"
                    fileCache[2] = "two"
                }
            }
            Thread.sleep((0L..20L).random())
            t.interrupt()
            t.join(20)

            // this test fails, because sometimes the cache directory
            // remains "locked to by this process" up to this point

            var ok: Boolean = false
            for (i in (1..10))
                try {

                    filecache<Int, String>(cacheDir).use { fileCache ->
                        (fileCache[1] == "one" || fileCache[1] == null).shouldBeTrue()
                        (fileCache[2] == "two" || fileCache[2] == null).shouldBeTrue()
                    }
                    ok = true

                    break

                } catch (e_: org.ehcache.StateTransitionException) {
                    Thread.sleep(100)
                    continue
                }
            ok.shouldBeTrue()
        }

    }
}

private data class SampleClass(val name: String, val tags: Set<String>) : java.io.Serializable