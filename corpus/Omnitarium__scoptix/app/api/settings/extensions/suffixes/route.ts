import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";

const createSchema = z.object({
  categoryId: z.number().int().positive(),
  suffix: z.string().min(1).max(64),
});

function normalizeSuffix(raw: string): string | null {
  let s = raw.trim().toLowerCase();
  if (!s) return null;
  if (!s.startsWith(".")) s = `.${s}`;
  if (s.length < 2) return null;
  return s;
}

export async function POST(req: Request) {
  const json = await req.json().catch(() => null);
  const parsed = createSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const suffix = normalizeSuffix(parsed.data.suffix);
  if (!suffix) {
    return NextResponse.json({ error: "Invalid suffix (e.g. use .pdf or pdf)" }, { status: 400 });
  }

  const cat = await prisma.extensionCategory.findUnique({ where: { id: parsed.data.categoryId } });
  if (!cat) {
    return NextResponse.json({ error: "Category not found" }, { status: 404 });
  }

  try {
    const row = await prisma.extensionSuffixRule.create({
      data: { extensionCategoryId: parsed.data.categoryId, suffix },
    });

    // Synchronize existing URLs with this new mapping
    await prisma.discoveredUrl.updateMany({
      where: { pathnameExtension: suffix },
      data: { extensionCategoryId: parsed.data.categoryId },
    });

    return NextResponse.json({ rule: row });
  } catch (e: unknown) {
    const code = typeof e === "object" && e && "code" in e ? (e as { code: string }).code : "";
    if (code === "P2002") {
      return NextResponse.json({ error: `Suffix ${suffix} is already mapped to a category` }, { status: 409 });
    }
    throw e;
  }
}
