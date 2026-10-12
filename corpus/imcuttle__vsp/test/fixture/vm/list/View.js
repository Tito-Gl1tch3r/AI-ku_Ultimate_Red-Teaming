/**
 * @file View
 * @author Cuttle Cong
 * @date 2018/5/10
 * @description
 */
import * as React from 'react'
import { binding } from 'react-mobx-vm'
import { Link } from 'react-router'

@binding
export default class View extends React.Component {
  renderItem({ name, email, phone, id }) {
    return (
      <div>
        <div>
          <label>Name: </label>
          <span>
            <Link to={`/detail/${id}`}>{name}</Link>
          </span>
        </div>
        <div>
          <label>Email: </label>
          <span>{email}</span>
        </div>
        <div>
          <label>Phone: </label>
          <span>{phone}</span>
        </div>
        <button onClick={() => this.onDelete(id)}>Delete</button>
      </div>
    )
  }

  onDelete = id => {
    const { list, person } = this.local
    fetch(`http://localhost:3000/users/${id}`, {
      method: 'DELETE',
      body: JSON.stringify(person),
      headers: {
        'Content-type': 'application/json; charset=UTF-8'
      }
    })
      .then(response => response.json())
      .then(json => {
        let index = list.findIndex(x => x.id === id)
        list.splice(index, 1)
      })
  }


  onAdd = () => {
    const { list, person } = this.local
    fetch('http://localhost:3000/users', {
      method: 'POST',
      body: JSON.stringify(person),
      headers: {
        'Content-type': 'application/json; charset=UTF-8'
      }
    })
      .then(response => response.json())
      .then(json => {
        list.push(json)
        person.assign({
          name: '',
          email: '',
          phone: ''
        })
      })
  }

  get addDisabled() {
    return this.local.person.name === ''
           || this.local.person.email === ''
           || this.local.person.phone === ''
  }

  render() {
    return (
      <div>
        <div>
          <input placeholder={'Name'} data-bind="person.name" />
          <input placeholder={'Email'} type="email" data-bind="person.email" />
          <input placeholder={'Phone'} type="phone" data-bind="person.phone" />
          <button disabled={this.addDisabled} onClick={this.onAdd}>Append</button>
        </div>
        <ul>
          {this.local.list.map((item, index) => (
            <li key={item.id}>{this.renderItem(item)}</li>
          ))}
        </ul>
      </div>
    )
  }
}
