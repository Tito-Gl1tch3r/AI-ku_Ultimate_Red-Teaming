/**
 * @file View
 * @author Cuttle Cong
 * @date 2018/5/10
 * @description
 */
import * as React from 'react'
import { binding } from 'react-mobx-vm'


@binding
export default class View extends React.Component {

  render() {
    return <div>
      <header>Im Header</header>
      <main>
        Im Content:
        <input data-bind="content" />
        <div>
          { this.props.children }
        </div>
      </main>
      <footer>
        Im Footer
      </footer>
    </div>
  }
}
