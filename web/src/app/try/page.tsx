import type { Metadata } from "next";
import WatershedApp from "@/components/WatershedApp";

export const metadata: Metadata = {
  title: "Try it — Watershed Signal",
  description: "Land cover, change detection, condition score, map, and field verification for the 3 trained sites.",
};

export default function Try() {
  return <WatershedApp />;
}
