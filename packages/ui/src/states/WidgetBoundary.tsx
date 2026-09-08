"use client";

import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { PartialFailureNotice } from "./index";

export interface WidgetBoundaryProps {
  /** 실패했을 때 사용자에게 보여줄 위젯 이름. */
  what: string;
  children: ReactNode;
}

interface WidgetBoundaryState {
  error: Error | null;
}

/** 위젯 하나의 실패를 그 자리에 가둔다.
 *
 * 대시보드에서 집계 하나가 실패했다고 화면 전체가 죽으면 안 된다는
 * `06_UI_UX_INFORMATION_ARCHITECTURE.md` 6절 요구를 구현한다.
 * 오류 경계는 아직 클래스 컴포넌트로만 만들 수 있다. */
export class WidgetBoundary extends Component<WidgetBoundaryProps, WidgetBoundaryState> {
  state: WidgetBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): WidgetBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 오류를 성공으로 숨기지 않는다. AGENTS.md 19절.
    console.error(`[widget:${this.props.what}]`, error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    const { error } = this.state;
    if (error) {
      return (
        <PartialFailureNotice
          what={this.props.what}
          traceId={(error as Error & { digest?: string }).digest}
          onRetry={this.handleRetry}
        />
      );
    }
    return this.props.children;
  }
}
