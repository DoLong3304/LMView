import React from "react";
import { LayoutType } from "./LayoutContext";

interface MultiChartContainerProps {
  layoutType: LayoutType;
  children: React.ReactNode;
}

const LAYOUT_CLASSES: Record<LayoutType, string> = {
  single: "grid-cols-1 grid-rows-1",
  "split-v": "grid-cols-2 grid-rows-1",
  "split-h": "grid-cols-1 grid-rows-2",
  quad: "grid-cols-2 grid-rows-2",
  "three-v": "grid-cols-3 grid-rows-1",
  "three-h": "grid-cols-1 grid-rows-3",
  six: "grid-cols-3 grid-rows-2",
};

export function getLayoutGridClass(type: LayoutType): string {
  return LAYOUT_CLASSES[type] ?? LAYOUT_CLASSES.single;
}

export function MultiChartContainer({ layoutType, children }: MultiChartContainerProps) {
  return (
    <div className={`grid gap-1 h-full w-full ${LAYOUT_CLASSES[layoutType]}`}>
      {React.Children.map(children, (child, index) => (
        <div
          key={index}
          className="relative min-w-0 min-h-0 overflow-hidden bg-gray-900 rounded"
        >
          {child}
        </div>
      ))}
    </div>
  );
}