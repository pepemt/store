import { useEffect, useRef } from "react";
import "../assets/styles/avatar.css";

type AvatarState = "standby" | "talking" | "thinking";

export default function Avatar({ state = "standby", className = "" }: { state?: AvatarState; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.classList.remove("state-standby", "state-talking", "state-thinking");
    el.classList.add(`state-${state}`);
  }, [state]);

  return (
    <div id="character" ref={ref} className={`state-standby ${className}`}>
      <div className="wrapper">
        <div className="border-circle" id="one"></div>
        <div className="border-circle" id="two"></div>

        <div className="background-circle">
          <div className="triangle-light"></div>

          <div className="body"></div>
          <div className="arm left"></div>
          <div className="arm right"></div>
          <div className="leg left"></div>
          <div className="leg right"></div>
        </div>

        <div className="head">
          <div className="face">
            <div className="hair-bottom"></div>

            <div className="eye-shadow" id="left">
              <div className="eye"></div>
            </div>

            <div className="eye-shadow" id="right">
              <div className="eyebrow"></div>
              <div className="eye"></div>
            </div>

            <div className="shadow-wrapper">
              <div className="shadow"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
