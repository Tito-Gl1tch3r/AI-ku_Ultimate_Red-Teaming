/*
 * SPDX-FileCopyrightText: (c) 2022 Artyom IG <github.com/rtmigo>
 * SPDX-License-Identifier: Apache-2.0
 */


import io.github.rtmigo.jaseca.*
import io.kotest.assertions.throwables.shouldThrow
import io.kotest.matchers.booleans.shouldBeTrue
import org.junit.jupiter.api.Test
import kotlin.io.path.exists

@OptIn(Experimental::class)
class TempDirsTest {
    @Test
    fun getTempDir() {
        println(systemTempDir())
        systemTempDir().exists().shouldBeTrue()
    }

    @Test
    fun `filecache created with id does not leave the temp dir`() {
        filecache<Int, Long>("a123")

        shouldThrow<IllegalIdException> {
            filecache<Int, Long>("x/y")
        }

        shouldThrow<IllegalIdException> {
            filecache<Int, Long>("../outer")
        }

        shouldThrow<IllegalIdException> {
            filecache<Int, Long>("")
        }
        shouldThrow<IllegalIdException> {
            filecache<Int, Long>("a123456789012345678901234567890")
        }
    }
}