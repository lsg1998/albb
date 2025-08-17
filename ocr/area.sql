-- 省市区数据表
-- 这是一个基础的省市区数据文件，用于初始化area.db数据库

-- 创建表结构
CREATE TABLE IF NOT EXISTS `area` (
  `id` int(11) NOT NULL,
  `parent_id` int(11) DEFAULT NULL,
  `name` varchar(50) NOT NULL,
  `province` varchar(50) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `county` varchar(50) DEFAULT NULL,
  `postcode` varchar(10) DEFAULT NULL,
  `parent_path` varchar(500) DEFAULT NULL,
  `level` int(11) DEFAULT NULL,
  `full_path` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

-- 插入基础数据（示例数据，实际使用时需要完整的省市区数据）
INSERT INTO `area` VALUES (1,0,'中国',NULL,NULL,NULL,NULL,'',0,'中国');
INSERT INTO `area` VALUES (110000,1,'北京市','北京市',NULL,NULL,NULL,'中国',1,'中国/北京市');
INSERT INTO `area` VALUES (110100,110000,'北京市','北京市','北京市',NULL,NULL,'中国/北京市',2,'中国/北京市/北京市');
INSERT INTO `area` VALUES (110101,110100,'东城区','北京市','北京市','东城区','100010','中国/北京市/北京市',3,'中国/北京市/北京市/东城区');
INSERT INTO `area` VALUES (110102,110100,'西城区','北京市','北京市','西城区','100032','中国/北京市/北京市',3,'中国/北京市/北京市/西城区');
INSERT INTO `area` VALUES (110105,110100,'朝阳区','北京市','北京市','朝阳区','100020','中国/北京市/北京市',3,'中国/北京市/北京市/朝阳区');
INSERT INTO `area` VALUES (310000,1,'上海市','上海市',NULL,NULL,NULL,'中国',1,'中国/上海市');
INSERT INTO `area` VALUES (310100,310000,'上海市','上海市','上海市',NULL,NULL,'中国/上海市',2,'中国/上海市/上海市');
INSERT INTO `area` VALUES (310101,310100,'黄浦区','上海市','上海市','黄浦区','200001','中国/上海市/上海市',3,'中国/上海市/上海市/黄浦区');
INSERT INTO `area` VALUES (310115,310100,'浦东新区','上海市','上海市','浦东新区','200120','中国/上海市/上海市',3,'中国/上海市/上海市/浦东新区');
INSERT INTO `area` VALUES (440000,1,'广东省','广东省',NULL,NULL,NULL,'中国',1,'中国/广东省');
INSERT INTO `area` VALUES (440300,440000,'深圳市','广东省','深圳市',NULL,NULL,'中国/广东省',2,'中国/广东省/深圳市');
INSERT INTO `area` VALUES (440305,440300,'南山区','广东省','深圳市','南山区','518052','中国/广东省/深圳市',3,'中国/广东省/深圳市/南山区');
INSERT INTO `area` VALUES (440306,440300,'宝安区','广东省','深圳市','宝安区','518101','中国/广东省/深圳市',3,'中国/广东省/深圳市/宝安区');
INSERT INTO `area` VALUES (528403,440300,'佛山市','广东省','佛山市',NULL,'528403','中国/广东省',2,'中国/广东省/佛山市');