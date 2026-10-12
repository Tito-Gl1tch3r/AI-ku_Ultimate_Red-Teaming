import { registerMenu } from './menu';
import { showModal } from './modal';

/**
 * 初始化UI界面
 * 注册油猴菜单并准备UI组件
 */
export function initUI(): void {
    // 注册油猴菜单
    registerMenu();
    
    // 注入全局样式
    injectGlobalStyles();
    
    // 加载Font Awesome
    loadFontAwesome();
}

/**
 * 加载Font Awesome
 */
function loadFontAwesome(): void {
    if (!document.querySelector('#font-awesome-css')) {
        const link = document.createElement('link');
        link.id = 'font-awesome-css';
        link.rel = 'stylesheet';
        link.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css';
        document.head.appendChild(link);
    }
}

/**
 * 注入全局样式
 */
function injectGlobalStyles(): void {
    const style = document.createElement('style');
    style.textContent = `
        /* 重置样式 */
        .jscookie-ui * {
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        }

        /* 全局动画 */
        @keyframes jscookie-fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes jscookie-slideInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes jscookie-slideInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes jscookie-scaleIn {
            from {
                opacity: 0;
                transform: scale(0.9);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes jscookie-pulse {
            0%, 100% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.05);
                opacity: 0.8;
            }
        }

        /* 平滑滚动 */
        .jscookie-ui {
            scroll-behavior: smooth;
        }

        /* 通用过渡效果 */
        .jscookie-ui button,
        .jscookie-ui input,
        .jscookie-ui select {
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* 焦点样式 */
        .jscookie-ui *:focus {
            outline: none;
        }

        .jscookie-ui button:focus-visible,
        .jscookie-ui input:focus-visible,
        .jscookie-ui select:focus-visible {
            box-shadow: 0 0 0 3px rgba(79, 125, 255, 0.2);
        }
    `;
    document.head.appendChild(style);
}

// 导出所有UI组件
export { registerMenu } from './menu';
export { showModal, hideModal } from './modal'; 