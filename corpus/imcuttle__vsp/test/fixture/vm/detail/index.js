/**
 * @file index
 * @author Cuttle Cong
 * @date 2018/5/10
 * @description
 */
import { bindView, Root, observable } from 'react-mobx-vm'
import Person from '../Person'

import View from './View'

@bindView(View)
export class Detail extends Person {
  init(props) {
    fetch(`http://localhost:3000/users/${this.id}`, {
      method: 'GET'
    })
      .then(res => res.json())
      .then(json => {
        this.assign(json)
      })
  }
}

export default Detail.create()
