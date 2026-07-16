


class DeliveryObj(object):
      """
      一个可以动态添加属性的对象
      支持通过点号语法和字典语法添加属性
      """
      
      def __init__(self, **kwargs):
            """
            初始化对象，可以传入初始属性
            """
            for key, value in kwargs.items():
                  setattr(self, key, value)
      
      def __setattr__(self, name, value):
            """
            重写设置属性方法，允许动态添加任何属性
            """
            object.__setattr__(self, name, value)
      
      def __getattr__(self, name):
            """
            当属性不存在时返回None而不是抛出异常
            """
            return None
      
      def add_attr(self, name, value):
            """
            显式添加属性的方法
            """
            setattr(self, name, value)
            return self
      
      def add_attrs(self, **kwargs):
            """
            批量添加多个属性
            """
            for key, value in kwargs.items():
                  setattr(self, key, value)
            return self
      
      def get_attrs(self):
            """
            获取所有属性（排除内置属性）
            """
            return {key: value for key, value in self.__dict__.items() 
                  if not key.startswith('_')}
            
      def get_attr(self, name):
            return getattr(self, name)
      
      def __str__(self):
            """
            字符串表示
            """
            attrs = self.get_attrs()
            if attrs:
                  attr_str = ', '.join([f"{k}={v}" for k, v in attrs.items()])
                  return f"DeliveryObj({attr_str})"
            return "DeliveryObj()"
      
      def __repr__(self):
            return self.__str__()


def main():
      # 创建对象
      delivery = DeliveryObj(name="测试商品", price=99.9)
      
      # 动态添加属性
      delivery.quantity = 10
      delivery.status = "待发货"
      
      # 使用方法添加属性
      delivery.add_attr("tracking_number", "TN123456789")
      delivery.add_attrs(
            customer_name="张三",
            address="北京市朝阳区",
            phone="13800138000"
      )
      
      # 打印所有属性
      print(delivery)
      """ 
      {'name': '测试商品', 'price': 99.9, 'quantity': 10, 'status': '待发货', 'tracking_number': 'TN123456789', 'customer_name': '张三', 'address': '北京市朝阳区', 'phone': '13800138000'}
      """
      print("所有属性:", delivery.get_attrs())

      print(delivery.get_attr('name'))


# main()
