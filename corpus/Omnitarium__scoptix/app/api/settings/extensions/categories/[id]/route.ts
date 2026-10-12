import { NextResponse } from "next/server";
import { z } from "zod";
import { CATEGORY_ICON_KEYS } from "@/lib/category-icons";
import { prisma } from "@/lib/prisma";

const patchSchema = z
  .object({
    displayName: z.string().min(1).max(120).optional(),
    slug: z
      .string()
      .min(1)
      .max(64)
      .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Slug: lowercase letters, numbers, hyphens only")
      .optional(),
    iconKey: z.enum(CATEGORY_ICON_KEYS).optional(),
  })
  .refine((d) => d.displayName !== undefined || d.slug !== undefined || d.iconKey !== undefined, {
    message: "At least one of displayName, slug, or iconKey is required",
  });

function parseId(raw: string): number | null {
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}

export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id: idStr } = await ctx.params;
  const id = parseId(idStr);
  if (!id) return NextResponse.json({ error: "Invalid id" }, { status: 400 });

  const json = await req.json().catch(() => null);
  const parsed = patchSchema.safeParse(json);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => i.message).join("; ") || "Invalid body";
    return NextResponse.json({ error: msg }, { status: 400 });
  }

  const existing = await prisma.extensionCategory.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Category not found" }, { status: 404 });

  const data: { displayName?: string; slug?: string; iconKey?: string } = {};
  if (parsed.data.displayName !== undefined) data.displayName = parsed.data.displayName.trim();
  if (parsed.data.slug !== undefined) data.slug = parsed.data.slug.trim().toLowerCase();
  if (parsed.data.iconKey !== undefined) data.iconKey = parsed.data.iconKey;

  if (data.slug !== undefined && data.slug !== existing.slug) {
    const clash = await prisma.extensionCategory.findUnique({ where: { slug: data.slug } });
    if (clash) return NextResponse.json({ error: "A category with this slug already exists" }, { status: 409 });
  }

  try {
    const row = await prisma.extensionCategory.update({ where: { id }, data });
    return NextResponse.json({ category: row });
  } catch (e: unknown) {
    const code = typeof e === "object" && e && "code" in e ? (e as { code: string }).code : "";
    if (code === "P2002") {
      return NextResponse.json({ error: "A category with this slug already exists" }, { status: 409 });
    }
    throw e;
  }
}

export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id: idStr } = await ctx.params;
  const id = parseId(idStr);
  if (!id) return NextResponse.json({ error: "Invalid id" }, { status: 400 });

  const existing = await prisma.extensionCategory.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Category not found" }, { status: 404 });

  await prisma.extensionCategory.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}
